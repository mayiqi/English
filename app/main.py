#! /usr/bin/python3
# -*- coding: utf-8 -*-

###########################################################################
# Copyright 2019 (C) Hui Lan <hui.lan@cantab.net>
# Written permission must be obtained from the author for commercial uses.
###########################################################################

from WordFreq import WordFreq
from wordfreqCMD import youdao_link, sort_in_descending_order
from UseSqlite import InsertQuery, RecordQuery
import pickle_idea, pickle_idea2
import os
import random, glob
from datetime import datetime, time
from flask import Flask, request, redirect, render_template, url_for, session, abort, flash, get_flashed_messages
from difficulty import get_difficulty_level, text_difficulty_level, user_difficulty_level

app = Flask(__name__)
app.secret_key = 'lunch.time!'

path_prefix = '/var/www/wordfreq/wordfreq/'
path_prefix = './' # comment this line in deployment

def get_random_image(path):
    img_path = random.choice(glob.glob(os.path.join(path, '*.jpg')))
    return img_path[img_path.rfind('/static'):]

def get_random_ads():
    ads = random.choice(['个性化分析精准提升', '你的专有单词本', '智能捕捉阅读弱点，针对性提高你的阅读水平'])
    return ads

def total_number_of_essays():
    rq = RecordQuery(path_prefix + 'static/wordfreqapp.db')
    rq.instructions("SELECT * FROM article")
    rq.do()
    result = rq.get_results()
    return  len(result)

def load_freq_history(path):
    d = {}
    if os.path.exists(path):
        d = pickle_idea.load_record(path)
    return d

def verify_user(username, password):
    rq = RecordQuery(path_prefix + 'static/wordfreqapp.db')
    rq.instructions_with_parameters("SELECT * FROM user WHERE name=? AND password=?", (username, password))
    rq.do_with_parameters()
    result = rq.get_results()
    return result != []

def add_user(username, password):
    start_date = datetime.now().strftime('%Y%m%d')
    expiry_date = '20211230'
    rq = InsertQuery(path_prefix + 'static/wordfreqapp.db')
    rq.instructions("INSERT INTO user Values ('%s', '%s', '%s', '%s')" % (username, password, start_date, expiry_date))
    rq.do()

def check_username_availability(username):
    rq = RecordQuery(path_prefix + 'static/wordfreqapp.db')
    rq.instructions("SELECT * FROM user WHERE name='%s'" % (username))
    rq.do()
    result = rq.get_results()
    return  result == []

def get_expiry_date(username):
    rq = RecordQuery(path_prefix + 'static/wordfreqapp.db')
    rq.instructions("SELECT expiry_date FROM user WHERE name='%s'" % (username))
    rq.do()
    result = rq.get_results()
    if len(result) > 0:
        return  result[0]['expiry_date']
    else:
        return '20191024'

def within_range(x, y, r):
    return x > y and abs(x - y) <= r 

def get_article_title(s):
    return s.split('\n')[0]

def get_article_body(s):
    lst = s.split('\n')
    lst.pop(0) # remove the first line
    return '\n'.join(lst) 

def appears_in_test(word, d):
    if not word in d:
        return ''
    else:
        return ','.join(d[word])

def get_time():
    return datetime.now().strftime('%Y%m%d%H%M') # upper to minutes

def get_question_part(s):
    s = s.strip()
    result = []
    flag = 0
    for line in s.split('\n'):
        line = line.strip()
        if line == 'QUESTION':
            result.append(line)
            flag = 1
        elif line == 'ANSWER':
            flag = 0
        elif flag == 1:
            result.append(line)
    return '\n'.join(result)

def get_answer_part(s):
    s = s.strip()
    result = []
    flag = 0
    for line in s.split('\n'):
        line = line.strip()
        if line == 'ANSWER':
            flag = 1
        elif flag == 1:
            result.append(line)

    js = '''
<script type="text/javascript">
    function toggle_visibility(id) {
       var e = document.getElementById(id);
       if(e.style.display == 'block')
          e.style.display = 'none';
       else
          e.style.display = 'block';
    }
</script>   
    '''
    html_code = js
    html_code += '\n'
    html_code += '<button onclick="toggle_visibility(\'answer\');">ANSWER</button>\n'
    html_code += '<div id="answer" style="display:none;">%s</div>\n' % ('\n'.join(result))
    return html_code
def get_answer_part(s):
    s = s.strip()
    result = []
    flag = 0
    for line in s.split('\n'):
        line = line.strip()
        if line == 'ANSWER':
            flag = 1
        elif flag == 1:
            result.append(line)
    js = '''
<script type="text/javascript">

    function toggle_visibility(id) {
       var e = document.getElementById(id);
       if(e.style.display == 'block')
          e.style.display = 'none';
       else
          e.style.display = 'block';
    }
</script>   
    '''
    html_code = js
    html_code += '\n'
    html_code += '<button onclick="toggle_visibility(\'answer\');">ANSWER</button>\n'
    html_code += '<div id="answer" style="display:none;">%s</div>\n' % ('\n'.join(result))
    return html_code

def get_flashed_messages_if_any():
    messages = get_flashed_messages()
    s = ''
    for message in messages:
        s += '<div class="alert alert-warning" role="alert">'
        s += f'Congratulations! {message}'
        s += '</div>'
    return s

def highlight(text, word):
    new_word = '<span style="background-color: yellow;">' + word + '</span>'  # 给单词加黄色高亮
    len_t = len(text)
    len_w = len(word)
    for i in range(len_t - len_w, -1, -1):
        if text[i: i + len_w] == word:
            text = text[:i] + new_word + text[i + len_w:]
    return text

@app.route("/<username>/reset", methods=['GET', 'POST'])
def user_reset(username):
    if request.method == 'GET':
        session['articleID'] = None
        return redirect(url_for('userpage', username=username))
    else:
        return 'Under construction'

@app.route("/mark", methods=['GET', 'POST'])
def mark_word():
    if request.method == 'POST':
        d = load_freq_history(path_prefix + 'static/frequency/frequency.p')
        lst_history = pickle_idea.dict2lst(d)
        lst = []
        for word in request.form.getlist('marked'):
            lst.append((word, 1))
        d = pickle_idea.merge_frequency(lst, lst_history)
        pickle_idea.save_frequency_to_pickle(d, path_prefix + 'static/frequency/frequency.p')
        return redirect(url_for('mainpage'))
    else:
        return 'Under construction'

@app.route("/", methods=['GET', 'POST'])
def mainpage():
    if request.method == 'POST':  # when we submit a form
        content = request.form['content']
        f = WordFreq(content)
        lst = f.get_freq()
        page = '<form method="post" action="/mark">\n'
        count = 1
        for x in lst:
            page += '<p><font color="grey">%d</font>: <a href="%s">%s</a> (%d)  <input type="checkbox" name="marked" value="%s"></p>\n' % (count, youdao_link(x[0]), x[0], x[1], x[0])
            count += 1
        page += ' <input type="submit" value="确定并返回"/>\n'
        page += '</form>\n'
        # save history 
        d = load_freq_history(path_prefix + 'static/frequency/frequency.p')
        lst_history = pickle_idea.dict2lst(d)
        d = pickle_idea.merge_frequency(lst, lst_history)
        pickle_idea.save_frequency_to_pickle(d, path_prefix + 'static/frequency/frequency.p')       
        return page
    elif request.method == 'GET': # when we load a html page
        su=session.get('username')
        gra=get_random_ads()
        tnof=total_number_of_essays()

        d = load_freq_history(path_prefix + 'static/frequency/frequency.p')

        return render_template('index.html',su=su,gra=gra,tnof=tnof)

@app.route("/<username>/mark", methods=['GET', 'POST'])
def user_mark_word(username):
    username = session[username]
    user_freq_record = path_prefix + 'static/frequency/' +  'frequency_%s.pickle' % (username)
    if request.method == 'POST':
        d = load_freq_history(user_freq_record)
        lst_history = pickle_idea2.dict2lst(d)
        lst = []
        for word in request.form.getlist('marked'):
            lst.append((word, [get_time()]))
        d = pickle_idea2.merge_frequency(lst, lst_history)
        pickle_idea2.save_frequency_to_pickle(d, user_freq_record)
        return redirect(url_for('userpage', username=username))
    else:
        return 'Under construction'

@app.route("/<username>/<word>/unfamiliar", methods=['GET', 'POST'])
def unfamiliar(username,word):
    user_freq_record = path_prefix + 'static/frequency/' + 'frequency_%s.pickle' % (username)
    pickle_idea.unfamiliar(user_freq_record,word)
    session['thisWord'] = word  # 1. put a word into session
    session['time'] = 1
    return redirect(url_for('userpage', username=username))

@app.route("/<username>/<word>/familiar", methods=['GET', 'POST'])
def familiar(username,word):
    user_freq_record = path_prefix + 'static/frequency/' + 'frequency_%s.pickle' % (username)
    pickle_idea.familiar(user_freq_record,word)
    session['thisWord'] = word  # 1. put a word into session
    session['time'] = 1
    return redirect(url_for('userpage', username=username))

@app.route("/<username>/<word>/del", methods=['GET', 'POST'])
def deleteword(username,word):
    user_freq_record = path_prefix + 'static/frequency/' + 'frequency_%s.pickle' % (username)
    pickle_idea2.deleteRecord(user_freq_record,word)
    flash(f'<strong>{word}</strong> is no longer in your word list.')
    return redirect(url_for('userpage', username=username))

@app.route("/<username>", methods=['GET', 'POST'])
def userpage(username):
    username = session.get('username')
    user_freq_record = path_prefix + 'static/frequency/' +  'frequency_%s.pickle' % (username)    
    if request.method == 'POST':  # when we submit a form
        content = request.form['content']
        f = WordFreq(content)
        lst = f.get_freq()
        page = '<meta charset="UTF8">'        
        page += '<meta name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=0.5, maximum-scale=3.0, user-scalable=yes" />'        
        page += '<p>勾选不认识的单词</p>'
        page += '<form method="post" action="/%s/mark">\n' % (username)
        page += ' <input type="submit" name="add-btn" value="加入我的生词簿"/>\n'        
        count = 1
        words_tests_dict = pickle_idea.load_record(path_prefix + 'static/words_and_tests.p')        
        for x in lst:
             page += '<p><font color="grey">%d</font>: <a href="%s" title="%s">%s</a> (%d)  <input type="checkbox" name="marked" value="%s"></p>\n' % (count, youdao_link(x[0]), appears_in_test(x[0], words_tests_dict), x[0], x[1], x[0])
             count += 1
        page += '</form>\n'
        return page
    
    elif request.method == 'GET': # when we load a html page
        gtaa=session['articleID']
        gfm=get_flashed_messages_if_any()
        rq = RecordQuery(path_prefix + 'static/wordfreqapp.db')
        if session['articleID']== None:    
            rq.instructions("SELECT * FROM article")
        else:
            rq.instructions('SELECT * FROM article WHERE article_id=%d' % gtaa)
        rq.do()
        result = rq.get_results()
        random.shuffle(result)

        # Choose article according to reader's level
        d1 = load_freq_history(path_prefix + 'static/frequency/frequency.p')
        d2 = load_freq_history(path_prefix + 'static/words_and_tests.p')
        d3 = get_difficulty_level(d1, d2)

        d = {}
        d_user = load_freq_history(user_freq_record)
        username = session.get('username')
        user_freq_record = path_prefix + 'static/frequency/' +  'frequency_%s.pickle' % (username)    
        newword = load_freq_history(user_freq_record)
        user_level = user_difficulty_level(d_user, d3) # more consideration as user's behaviour is dynamic. Time factor should be considered.
        random.shuffle(result) # shuffle list
        d = random.choice(result)
        text_level = text_difficulty_level(d['text'], d3)
        if session['articleID'] == None:
            for reading in result:
                text_level = text_difficulty_level(reading['text'], d3)
                factor = random.gauss(0.8, 0.1) 
                if within_range(text_level, user_level, (8.0 - user_level)*factor):
                    d = reading
                    break

        article_title = get_article_title(d['text'])
        article_body = get_article_body(d['text'])
        if len(newword) > 0:
                lst = pickle_idea2.dict2lst(newword)
                lst2 = []
                for t in lst:
                    lst2.append((t[0],len(t[1])))
                for x in lst2:
                    print(x[0])
                    article_title  = highlight(article_title,x[0])
                    article_body = highlight(article_body,x[0])

        ddate=d['date']
        dsource=d['source']
        gqp=get_question_part(d['question'])
        gap=get_answer_part(d['question'])
        session['articleID'] = d['article_id']

        d = load_freq_history(user_freq_record)
        page=''
        if len(d) > 0:
            page += '<p><b>我的生词簿</b></p>'
            lst = pickle_idea2.dict2lst(d)
            lst2 = []
            for t in lst:
                lst2.append((t[0], len(t[1])))
            for x in sort_in_descending_order(lst2):
                word = x[0]
                freq = x[1]
                if session.get('thisWord') == x[0] and session.get('time') == 1:
                    page += '<a name="aaa"></a>'    
                    session['time'] = 0   
                if isinstance(d[word], list): 
                    if freq > 1:
                        page += '<p class="new-word"> <a class="btn btn-light" href="%s" role="button">%s</a>(<a title="%s">%d</a>) <a class="btn btn-success" href="%s/%s/familiar" role="button">熟悉</a> <a class="btn btn-warning" href="%s/%s/unfamiliar" role="button">不熟悉</a>  <a class="btn btn-danger" href="%s/%s/del" role="button">删除</a> </p>\n' % (youdao_link(word), word, '; '.join(d[word]), freq,username, word,username,word, username,word)
                    else:
                        page += '<p class="new-word"> <a class="btn btn-light" href="%s" role="button">%s</a>(<a title="%s">%d</a>) <a class="btn btn-success" href="%s/%s/familiar" role="button">熟悉</a> <a class="btn btn-warning" href="%s/%s/unfamiliar" role="button">不熟悉</a>  <a class="btn btn-danger" href="%s/%s/del" role="button">删除</a> </p>\n' % (youdao_link(word), word, '; '.join(d[word]), freq,username, word,username,word, username,word)
                elif isinstance(d[word], int): 
                    page += '<a href="%s">%s</a>%d\n' % (youdao_link(word), word, freq)
        return render_template('today_article.html',page =page,gtaa=gtaa,gfm=gfm,username=username,ddate=ddate,article_title=article_title,article_body=article_body,dsource=dsource,gqp=gqp,user_level=user_level,text_level=text_level)


@app.route("/signup", methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')
    elif request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        available = check_username_availability(username)
        if not available:
            flash('用户名 %s 已经被注册。' % (username))
            return render_template('signup.html')
        elif len(password.strip()) < 4:
            return '密码过于简单。'
        else:
            add_user(username, password)
            verified = verify_user(username, password)
            if verified:
                session['logged_in'] = True
                session[username] = username
                session['username'] = username
                session['expiry_date'] = get_expiry_date(username)
                session['articleID'] = None
                return '<p>恭喜，你已成功注册， 你的用户名是 <a href="%s">%s</a>。</p>\
                <p><a href="/%s">开始使用</a> <a href="/">返回首页</a><p/>' % (username, username, username)
            else:
                return '用户名密码验证失败。'


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if not session.get('logged_in'):
            return render_template('login.html')
        else:
            return '你已登录 <a href="/%s">%s</a>。 登出点击<a href="/logout">这里</a>。' % (session['username'], session['username'])
    elif request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        verified = verify_user(username, password)
        if verified:
            session['logged_in'] = True
            session[username] = username
            session['username'] = username
            user_expiry_date = get_expiry_date(username)
            session['expiry_date'] = user_expiry_date
            session['articleID'] = None
            return render_template('today_article.html',username=username)  #redirect(url_for('userpage', username=username))
        else:
            return '无法通过验证。'


@app.route("/logout", methods=['GET', 'POST'])
def logout():
    session['logged_in'] = False
    return render_template('index.html')  


if __name__ == '__main__':
    app.run(debug=True)        
