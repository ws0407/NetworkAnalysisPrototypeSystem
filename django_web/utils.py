import datetime
import os

import paramiko
from pyDes import *
import base64, time
import threading
from .models import *
from NetworkAnalysisPrototypeSystem.settings import DATASETS_ROOT, DES_KEY, DES_IV, DEBUG


class execJobThread(threading.Thread):
    def __init__(self, submit_time):
        super().__init__()
        self.submit_time = submit_time

    def run(self):
        job = Job.objects.get(submit_time=self.submit_time)
        driver = Driver.objects.get(id=job.driver)
        if driver.status == 'error':
            job.start_time = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
            job.end_time = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
            job.status = 'error'
            job.save()
            return
        # while driver.status == 'working':
        #     print('waiting {}'.format(driver.ip))
        #     if DEBUG:
        #         time.sleep(5)
        #     else:
        #         time.sleep(10)
        #     driver = Driver.objects.get(id=job.driver)
        SELF = (driver.ip == '101.43.253.225')
        L = None
        if not SELF:
            des3 = Des3(DES_KEY, DES_IV)
            L = LinuxOrder(driver.ip, driver.port, driver.username, des3.decrypt(driver.password), 5)
            if L.status != 'available':
                L = LinuxOrder(driver.ip, driver.port, driver.username, des3.decrypt(driver.password), 5)
                if L.status != 'available':
                    job.start_time = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
                    job.end_time = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
                    job.status = 'error'
                    job.save()
                    return
        # driver.status = 'working'
        job.start_time = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        job.status = 'running'
        # driver.save()
        job.save()
        f_d = Function_Driver.objects.get(function_id=Function.objects.get(name=job.type).id, driver_id=driver.id)
        for path in job.path.split('%'):
            path = path.replace('\\', '/')
            if len(path) > 0 and os.path.exists(path):
                print("sudo scp {} {}@{}:{}".format(path, driver.username, driver.ip, f_d.data_dir))
                if DEBUG:
                    input("sudo copy {} ok ?".format(path))
                else:
                    if SELF:
                        os.system("sudo cp -r {} {}".format(path, f_d.data_dir))
                    else:
                        os.system("sudo scp {} {}@{}:{}".format(path, driver.username, driver.ip, f_d.data_dir))
        if DEBUG:
            print("nohup " + f_d.python_path + " " + f_d.code_path + " >> " + os.path.join(f_d.result_path, 'log.txt') + " 2>&1 &")
        else:
            if SELF:
                os.system("nohup " + f_d.python_path + " " + f_d.code_path + " >> " + os.path.join(f_d.result_path, 'log.txt') + " 2>&1 &")
                pid = os.popen("sudo ps -aux | grep " + f_d.python_path + " | grep -v grep | awk '{print $2}'").readlines()
                pid = pid[0].replace("\n", "") if len(pid) > 0 else ''
            else:
                L.run("nohup " + f_d.python_path + " " + f_d.code_path + " >> " + os.path.join(f_d.result_path, 'log.txt') + " 2>&1 &")
                pid = L.run("sudo ps -aux | grep " + f_d.python_path + " | grep -v grep | awk '{print $2}'")
            job.pid = int(str(pid)) if str(pid).isdigit() else 0
            job.save()
        while True and not DEBUG:
            if SELF:
                pid = os.popen("sudo ps -aux | grep " + f_d.python_path + " | grep -v grep | awk '{print $2}'").readlines()
                pid = pid[0].replace("\n", "") if len(pid) > 0 else ''
                res = os.popen("sudo find " + f_d.result_path + " -name 'result.json'").read()
            else:
                pid = L.run("sudo ps -aux | grep " + f_d.python_path + " | grep -v grep | awk '{print $2}'")
                res = L.run("sudo find " + f_d.result_path + " -name 'result.json'")
            if len(str(res)) > 1:
                # print(res)
                break
            if not pid.isdigit():
                job.end_time = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
                job.status = 'error'
                job.save()
                # driver.status = 'available'
                # driver.save()
                return
            time.sleep(10)
        job.end_time = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        job.status = 'finished'
        job.save()
        # driver.status = 'available'
        # driver.save()
        if DEBUG:
            print("sudo scp -r " + driver.username + "@" + driver.ip + ":" + f_d.result_path + " " + job.result_path)
            input("sudo copy {} ok ?".format(f_d.result_path))
        else:
            if SELF:
                os.system("sudo cp -r " + f_d.result_path + " " + job.result_path)
            else:
                os.system("sudo scp -r " + driver.username + "@" + driver.ip + ":" + f_d.result_path + " " + job.result_path)
        if DEBUG:
            print("sudo rm -rf {}/*".format(f_d.data_dir))
            print("sudo rm -f {}".format(f_d.result_path + "/result.json"))
        else:
            if SELF:
                os.system("sudo rm -rf {}/*".format(f_d.data_dir))
                os.system("sudo rm -f {}".format(f_d.result_path + "/result.json"))
            else:
                L.run("sudo rm -rf {}/*".format(f_d.data_dir))
                L.run("sudo rm -f " + f_d.result_path + "/result.json")
                L.close_ssh()
        print('job thread ok!')


def check_attachments(paths, job_type):
    paths = paths.replace('\\', '/').split('%')
    paths = [path for path in paths if len(path) > 5]
    job_type = job_type.lower()
    flag = True
    if 'behavior' in job_type:
        if len(paths) != 1 or paths[0][-4:] != '.csv':
            flag = False
    elif 'application' in job_type:
        if len(paths) != 2 or paths[0][-4:] != '.npy' or paths[1][-4:] != '.npy':
            flag = False
        if 'sample' not in paths[0] and 'sample' not in paths[1]:
            flag = False
        if 'label' not in paths[0] and 'label' not in paths[1]:
            flag = False
    elif 'popularity' in job_type:
        if len(paths) != 1 or paths[0][-4:] != '.pkl':
            flag = False
    elif 'bgp' in job_type:
        for path in paths:
            if path[-4:] != '.csv':
                flag = False
    elif 'flow' in job_type:
        if len(paths) != 1 or paths[0][-5:] != '.pcap':
            flag = False
    if not flag:
        for path in paths:
            if len(path) > 0 and os.path.exists(path):
                if DEBUG:
                    pass
                else:
                    os.system("sudo rm -f {}".format(path))
    return flag


def delete_one_job(job_id):
    try:
        job = Job.objects.get(id=job_id)
        data_path = job.path.replace('\\', '/').split('%')
        if DEBUG:
            for p in data_path:
                if len(p) > 0:
                    print("sudo rm -rf {}".format(p))
            print("sudo rm -rf {}".format(job.result_path))
        else:
            for p in data_path:
                if len(p) > 0 and os.path.exists(p):
                    os.system("sudo rm -rf {}".format(p))
            if os.path.exists(job.result_path):
                os.system("sudo rm -rf {}".format(job.result_path))
        Job.objects.filter(id=job_id).delete()
        return True
    except Exception as e:
        print(e)
        return False


def delete_one_driver(driver_id):
    try:
        driver_ = Driver.objects.get(id=driver_id)
        jobs = Job.objects.filter(driver=driver_.id)
        for job in jobs:
            if not delete_one_job(job.id):
                return False
        return True
    except:
        return False