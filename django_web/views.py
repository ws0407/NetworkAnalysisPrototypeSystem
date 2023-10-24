import random
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
import json, time, datetime

from NetworkAnalysisPrototypeSystem.settings import DATASETS_ROOT, DES_KEY, DES_IV, AUTH_CODE, MEDIA_DIR
from .models import *
import os
from pathlib import Path
import time, datetime
import markdown
from .utils import *


def my_login(request):
    if request.method == 'GET':
        return render(request, 'login.html', {'response': json.dumps('')})
    else:
        username = request.POST.get("email")
        password = request.POST.get("password")
        remember = request.POST.get("remember")
        if not User.objects.filter(username=username).exists():
            if User.objects.filter(email=username).exists():
                username = User.objects.get(email=username).username
            else:
                return HttpResponse(json.dumps({'response': '[Sign in failed] Username or Email dose not exist!'}))
        # if email == 'sswang@bupt.edu.cn' and password == 'pbkdf2_sha256$260000$CxR0JiVF7DPZTa2zGMeAW1$FOY+50ZZRRA/QrjERL8yf3u/Avc0IUeDE+7kekV/fQQ=':
        user = authenticate(username=username, password=password)
        if not user:
            username = User.objects.filter(email=username)
            user = User.objects.get(username=username, password=password)
        if user:
            login(request, user)
            request.session['username'] = username
            if remember:
                request.session.set_expiry(None)
            else:
                request.session.set_expiry(0)
            print(str(request.GET.get('next', '/')))
            return HttpResponse(json.dumps({'response': 'Sign in successfully!', 'redirect': str(request.GET.get('next', '/'))}))
        return HttpResponse(json.dumps({'response': '[Sign in failed] Email or password wrong!'}))


def register(request):
    if request.method == 'GET':
        return render(request, 'register.html', {'response': json.dumps('')})
    else:
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        auth_code = request.POST.get("auth_code")
        if auth_code != AUTH_CODE:
            return HttpResponse(json.dumps({'response': 'Auth Code Wrong!'}))
        if User.objects.filter(username=username).exists():
            return HttpResponse(json.dumps({'response': 'Username already exists!'}))
        if User.objects.filter(email=email).exists():
            return HttpResponse(json.dumps({'response': 'Email already exists!'}))
        User.objects.create_user(username=username, password=password, email=email)
        return HttpResponse(json.dumps({'response': 'Sign up successfully!'}))


def my_logout(request):
    logout(request)
    return redirect('/login/')


@login_required
def index(request):
    if request.is_ajax():
        print(request.POST)
        cmd = request.POST.get("cmd")
        print(cmd)
        if cmd == "time":
            response = JsonResponse({"time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
            return response
        else:
            return JsonResponse({"time": "failed"})
    return render(request, 'index.html')


@login_required
def home(request):
    jobs = Job.objects.all()
    drivers = Driver.objects.all()
    functions = Function.objects.all()
    # functions = [f.name for f in functions]
    job_nums = [0] * len(functions)
    for job in jobs:
        for i in range(len(functions)):
            if job.type == functions[i].name:
                job_nums[i] += 1
    driver_status = ['Available', 'Working', 'Error']
    driver_nums = [0] * len(driver_status)
    for d in drivers:
        for i in range(len(driver_status)):
            if d.status.lower() == driver_status[i].lower():
                driver_nums[i] += 1
    return render(request, 'home.html', {'jobs': jobs, 'drivers': drivers, 'functions': functions, 'job_nums': job_nums, 'driver_nums': driver_nums, 'driver_status': driver_status})


@login_required
def status(request, driver_id=1):
    try:
        driver_id = int(driver_id)
    except:
        print('illegal input driver_id')
        driver_id = 1
    _driver = Driver.objects.filter(id=driver_id)
    if len(_driver) == 0:
        _driver = Driver.objects.get(id=1)
    else:
        _driver = _driver[0]
    jobs = Job.objects.filter(driver=driver_id)
    return render(request, 'status.html', {'driver': _driver, 'jobs': jobs})


@login_required
def subtask(request, subtask_name=''):
    try:
        function = Function.objects.get(name=subtask_name)
    except:
        function = Function.objects.get(name='Wrong Task')
    jobs = Job.objects.filter(type=subtask_name)
    function.markdown = markdown.markdown(function.markdown, extensions=[
        'markdown.extensions.extra',
        'markdown.extensions.codehilite',
        'markdown.extensions.toc',
    ])
    function.code = markdown.markdown(function.code, extensions=[
        'markdown.extensions.extra',
        'markdown.extensions.codehilite',
        'markdown.extensions.toc',
    ])
    # if os.path.exists(os.path.join(job.result_path, 'result/result.json')):
    #     with open(os.path.join(job.result_path, 'result/result.json')) as f:
    #         job_results = json.load(f)
    #     for res in job_results:
    #         if res['type'] == 'image':
    #             res['data'] = job.submit_time + '/result/' + res['data']
    #         if res['type'] == 'table':
    #             res['data']['thead'] = ['#'] + res['data']['thead']
    #             for i in range(len(res['data']['tbody'])):
    #                 res['data']['tbody'][i] = [str(i)] + res['data']['tbody'][i]
    # else:
    #     job_results = [{
    #         'type': 'text',
    #         'title': job.status,
    #         'data': 'No results yet'
    #     }]
    return render(request, 'subtask.html', {'jobs': jobs, 'function': function})


@login_required
def get_result(request):
    try:
        job_id = request.POST.get("job_id")
        job_id = int(job_id)
    except:
        print('illegal input job id')
        job_id = 1
    job = Job.objects.filter(id=job_id)
    if len(job) == 0:
        job = Job.objects.get(id=1)
    else:
        job = job[0]

    if os.path.exists(os.path.join(MEDIA_DIR, job.submit_time, 'result/result.json')):
        with open(os.path.join(MEDIA_DIR, job.submit_time, 'result/result.json'), encoding='utf-8') as f:
            job_results = json.load(f)
        for res in job_results:
            if res['type'] == 'image':
                res['data'] = job.submit_time + '/result/' + res['data']
            if res['type'] == 'table':
                res['data']['thead'] = ['#'] + res['data']['thead']
                for i in range(len(res['data']['tbody'])):
                    res['data']['tbody'][i] = [str(i)] + res['data']['tbody'][i]
    else:
        # job_results = [
        #     {
        #         "type": "table",
        #         "title": "Test Table 1",
        #         "description": "This is a test description for the table",
        #         "data": {
        #             "thead": ["1", "2", "3", "4"],
        #             "tbody": [
        #                 ["a", "b", "c", "d"],
        #                 ["e", "f", "g", "h"]
        #             ]
        #         }
        #     },
        #     {
        # 、        "type": "table",
        #         "title": "Test Table 2",
        #         "data": {
        #             "thead": ["11", "22", "32", "42"],
        #             "tbody": [
        #                 ["a1", "ba", "cf", "def"],
        #                 ["ea", "fd", "gfe", "he"],
        #                 ["a1", "ba", "cf", "def"],
        #             ]
        #         }
        #     },
        #     {
        #         "type": "line chart",
        #         "title": "Test line chart",
        #         "description": "This is a test description for the chart",
        #         "labels": [i for i in range(100)],
        #         "yTitle": "Sale",
        #         'xTitle': "Month",
        #         "data": [
        #             {
        #               "name": "",
        #               "data": [random.random() for i in range(100)]
        #             },
        #             {
        #               "name": "Electronics",
        #               "data": [random.random() for i in range(100)]
        #             },
        #         ]
        #     },
        #     {
        #         "type": "bar chart",
        #         "title": "Test bar chart",
        #         "description": "This is a test description for the chart",
        #         "labels": ["January", "February", "March", "April", "May", "June", "July"],
        #         "yTitle": "Sale",
        #         "data": [
        #             {
        #               "name": "Digital Goods",
        #               "data": [28, 48, 40, 19, 86, 27, 90]
        #             },
        #             {
        #               "name": "Electronics",
        #               "data": [65, 59, 80, 81, 56, 55, 40]
        #             },
        #         ]
        #     },
        #     {
        #         "type": "image",
        #         "title": "Test Image",
        #         "description": "This is a test description for the Image",
        #         "data": "BGP.png"
        #     },
        #     {
        #         "type": "bar chart",
        #         "title": "Test bar chart",
        #         "description": "This is a test description for the chart",
        #         "labels": ["January", "February", "March", "April", "May", "June", "July"],
        #         "yTitle": "Sale",
        #         "data": [
        #             {
        #               "name": "Digital Goods",
        #               "data": [28, 48, 40, 19, 86, 27, 90]
        #             },
        #             {
        #               "name": "Electronics",
        #               "data": [65, 59, 80, 81, 56, 55, 40]
        #             },
        #         ]
        #     },
        #     {
        #         "type": "text",
        #         "data": "xxx"
        #     }
        # ]

        job_results = [{
            'type': 'text',
            'title': job.status,
            'data': 'No results yet'
        }]


    return HttpResponse(json.dumps(job_results))


@login_required
def upload(request):
    file = request.FILES.get('file')  # 获取文件对象，包括文件名文件大小和文件内容
    current_time = time.strftime("%Y%m%d%H%M%S")
    # 规定上传目录
    upload_url = os.path.join(DATASETS_ROOT, current_time)
    # 判断文件夹是否存在
    folder = os.path.exists(upload_url)
    if not folder:
        os.makedirs(upload_url)
        # print("创建文件夹")
    if file:
        file_name = file.name
        # 判断文件是是否重名，懒得写随机函数，重名了，文件名加时间
        if os.path.exists(os.path.join(upload_url, file_name)):
            name, etx = os.path.splitext(file_name)
            addtime = time.strftime("%H%M%S")
            finally_name = name + "_" + addtime + etx
            # print(name, etx, finally_name)
        else:
            finally_name = file.name
        # 文件分块上传
        upload_file_to = open(os.path.join(upload_url, finally_name), 'wb+')
        print(upload_file_to)
        for chunk in file.chunks():
            upload_file_to.write(chunk)
        upload_file_to.close()
        # 返回文件的URl
        file_upload_url = DATASETS_ROOT + current_time + '\\' + finally_name
        # 构建返回值
        response_data = {'FileName': file_name, 'FileUrl': file_upload_url}
        response_json_data = json.dumps(response_data)  # 转化为Json格式
        return HttpResponse(response_json_data)
    else:
        print('no file')


@login_required
def add_task(request):
    name = request.POST.get('name')
    job_type = request.POST.get('job_type')
    file_paths = request.POST.get('file_path')
    if not check_attachments(file_paths, job_type):
        return HttpResponse(json.dumps({'Status': 'The uploaded attachment does not meet the requirements.'}))
    try:
        function_id = Function.objects.get(name=job_type).id
        # _driver = Driver.objects.get(name=request.POST.get('driver'))
        f_d = Function_Driver.objects.get(function_id=function_id)
        # des3 = Des3(DES_KEY, DES_IV)
        # if f_d.is_public == 0:
        #     username = request.POST.get('username')
        #     password = request.POST.get('password')
        #     if username != _driver.username or des3.encrypt(password) != _driver.password:
        #         return HttpResponse(json.dumps({'Status': 'The username or password of the server is incorrect.'}))
        # else:
        #     username = _driver.username
        #     password = des3.decrypt(_driver.password)
        # L = LinuxOrder(_driver.ip, _driver.port, username, password, 5)
        # L_status = L.status
        # L.close_ssh()
        # if L_status != 'available':
        #     return HttpResponse(json.dumps({'Status': 'Server connection failed.'}))

        submit_time = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        result_path = os.path.join(DATASETS_ROOT, 'result', submit_time)
        if not os.path.exists(result_path):
            os.makedirs(result_path)
            # print("创建文件夹")
        Job.objects.create(
            name=name,
            type=job_type,
            submit_time=submit_time,
            start_time='#',
            end_time='#',
            status='waiting',
            path=file_paths,
            driver=f_d.driver_id,
            result_path=result_path + '/'
        )
        exec_job = execJobThread(submit_time)
        exec_job.start()
        job_id = Job.objects.get(submit_time=submit_time).id
        return HttpResponse(json.dumps({'Status': 'ok', 'job_id': str(job_id)}))
    except Exception as e:
        print('[error]', e)
        return HttpResponse(json.dumps({'Status': 'database error '.format(e)}))