from django.db import models
from django import forms
from mdeditor.fields import MDTextField
import paramiko
from pyDes import *
import base64


# Create your models here.
class Job(models.Model):
    class Meta:
        db_table = 'job'

    id = models.IntegerField(primary_key=True, unique=True, auto_created=True)
    name = models.CharField(max_length=45)
    type = models.CharField(max_length=45)
    submit_time = models.CharField(max_length=45)
    start_time = models.CharField(max_length=45)
    end_time = models.CharField(max_length=45)
    status = models.CharField(max_length=45)
    path = models.CharField(max_length=4096)
    driver = models.IntegerField()
    result_path = models.CharField(max_length=256)
    pid = models.IntegerField()


class Driver(models.Model):
    class Meta:
        db_table = 'driver'

    id = models.IntegerField(primary_key=True, unique=True, auto_created=True)
    ip = models.CharField(max_length=45)
    username = models.CharField(max_length=45)
    password = models.CharField(max_length=45)
    type = models.CharField(max_length=10)
    name = models.CharField(max_length=45)
    port = models.IntegerField()
    status = models.CharField(max_length=45)
    memory = models.FloatField()
    cpu = models.FloatField()
    storage = models.FloatField()
    osinfo = models.CharField(max_length=45)
    edit_time = models.CharField(max_length=45)


class Function_Driver(models.Model):
    class Meta:
        db_table = 'function_driver'
    id = models.IntegerField(primary_key=True, unique=True, auto_created=True)
    function_id = models.IntegerField()
    driver_id = models.IntegerField()
    data_dir = models.CharField(max_length=128)
    python_path = models.CharField(max_length=128)
    code_path = models.CharField(max_length=128)
    result_path = models.CharField(max_length=128)
    is_public = models.IntegerField()
    is_default = models.IntegerField()
    description = models.TextField()
    edit_time = models.CharField(max_length=45)
    requirement = models.TextField()


class Function(models.Model):
    class Meta:
        db_table = 'function'

    id = models.IntegerField(primary_key=True, unique=True, auto_created=True)
    name = models.CharField(max_length=128)
    description = models.TextField()
    code = MDTextField()
    markdown = MDTextField()
    name_zh = MDTextField()
    attachment = models.TextField()


class Des3(object):
    def __init__(self, key, iv):
        # 这里密钥key长度必须为16/24, ,偏移量ivs
        self.key = key
        self.mode = CBC
        self.iv = iv

    # 加密函数，如果text不是16的倍数【加密文本text必须为16的倍数！】，那就补足为16的倍数
    def encrypt(self, text):
        des3 = triple_des(self.key, self.mode, self.iv, pad=None, padmode=PAD_PKCS5)
        data = des3.encrypt(text)
        data = base64.b64encode(data)
        return data.decode('utf-8')

    # 解密后，去掉补足的空格用strip() 去掉
    def decrypt(self, data):
        des3 = triple_des(self.key, self.mode, self.iv, pad=None, padmode=PAD_PKCS5)
        data = base64.b64decode(data)
        text = des3.decrypt(data)
        return text.decode()


class LinuxOrder:

    def __init__(self, ip, port, username, password, timeout):
        """
        :param ip: server IP
        :param port: ssh connection port
        :param username: service username
        :param password: service password
        :param timeout: service timeout
        :return: connection status
        """
        try:
            self.ip = ip
            self.port = port
            self.username = username
            self.password = password
            self.timeout = timeout
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(self.ip, self.port, self.username, self.password, timeout=self.timeout)
            print('{0}：连接成功'.format(self.ip))
            self.status = 'available'
        except Exception as e:
            print('[error]{0}\n{1}: connection failed'.format(e, self.ip))
            self.status = 'error'

    def run(self, order):
        """
        :param order: command to run in cmd window
        :return: run result
        """
        try:
            self.status = 'working'
            stdin, stdout, stderr = self.ssh.exec_command(order)
            self.status = 'available'
            print(stdin.read().decode(), stdout.read().decode(), stderr.read().decode())
            return stdout.read().decode()
        except Exception as e:
            self.status = 'error'
            print('[error]{0}\n{1}: run cmd failed, in {2}'.format(e, self.ip, order))
            return 'error'

    def close_ssh(self):
        """close ssh connection"""
        self.status = 'available'
        self.ssh.close()
        print('关闭ssh连接')
