# Author:Pegasus-Yang
# Time:2020/3/21 22:40
import subprocess
import json


class STFConnect:

    def __init__(self):
        self.token = 'Enter your token here'
        self.stf_url = 'http://127.0.0.1:7100'
        self.divice_dict = {}

    def set_token(self, new_token):
        """设置token"""
        self.token = new_token

    def set_stf_url(self, new_url):
        """设置stf的url"""
        self.stf_url = new_url

    def get_adb_devices_list(self):
        """获取本地adb的设备列表"""
        return subprocess.run('adb devices', capture_output=True).stdout.decode('utf-8')

    def get_stf_devices_list(self):
        """获取stf端的设备列表(因为手头都是模拟器所以针对模拟器关键字做了过滤)"""
        stf_devices_list_sub = subprocess.run(
            'curl.exe -H "Authorization: Bearer {token}" {stf_url}/api/v1/devices'.format(
                token=self.token, stf_url=self.stf_url), capture_output=True)
        list_json = json.loads(stf_devices_list_sub.stdout.decode('utf-8'))
        result_list = []
        for i in list_json['devices']:
            if 'emulator' in i['serial']:
                result_list.append(i['serial'])
        return result_list

    def add_device(self, device_serial):
        """从stf获取一台设备的授权"""
        result = subprocess.run(
            'curl.exe -X POST -H "Content-Type: application/json"  -H "Authorization: Bearer {token}" --data "{{\\\"serial\\\": \\\"{device_serial}\\\"}}" {stf_url}/api/v1/user/devices'.format(
                token=self.token, device_serial=device_serial, stf_url=self.stf_url),
            capture_output=True).stdout.decode('utf-8')
        result = json.loads(result)
        if result['success'] is True:
            self.divice_dict[device_serial] = '1'
            return True
        return False

    def remote_connect(self, device_serial):
        """从stf获取一台设备的远程连接地址，并使用adb进行连接(该设备首先需要获取授权)"""
        resultf = subprocess.run(
            'curl.exe -X POST  -H "Authorization: Bearer {token}" {stf_url}/api/v1/user/devices/{device_serial}/remoteConnect'.format(
                token=self.token, device_serial=device_serial, stf_url=self.stf_url),
            capture_output=True).stdout.decode('utf-8')
        resultf = json.loads(resultf)
        if resultf['success'] is True:
            url = resultf['remoteConnectUrl']
            result = subprocess.run('adb connect {url}'.format(url=url), capture_output=True).stdout.decode('utf-8')
            if 'authenticate' in result:
                self.divice_dict[device_serial] = url
                return True
        return False

    def remote_disconnect(self, device_serial):
        """通过adb断开与设备的连接"""
        result = subprocess.run('adb disconnect {device_serial}'.format(device_serial=device_serial),
                                capture_output=True).stderr.decode('utf-8')
        if 'no such device' in result:
            return False
        return True

    def remove_device(self, device_serial):
        """从stf撤销一台设备的授权（该设备应先断开连接）"""
        result = subprocess.run(
            'curl.exe -X DELETE -H "Authorization: Bearer {token}" {stf_url}/api/v1/user/devices/{device_serial}'.format(
                token=self.token, device_serial=device_serial, stf_url=self.stf_url),
            capture_output=True).stdout.decode('utf-8')
        result = json.loads(result)
        if result['success'] is True:
            self.divice_dict[device_serial] = '0'
            return True
        return False

    def device_list(self):
        """获取记录中的设备列表"""
        result = []
        for device in self.divice_dict.keys():
            if self.divice_dict[device] != '0':
                result.append(['设备名：'+str(device), '地址：'+str(self.divice_dict[device])])
        return result

def connect_all_emulator(stf: STFConnect):
    """一键连接全部远程模拟器"""
    stf_list = stf.get_stf_devices_list()
    for i in stf_list:
        if 'emulator' not in i:
            stf_list.remove(i)
    for device in stf_list:
        stf.add_device(device)
    for device in stf.divice_dict.keys():
        stf.remote_connect(device)


def disconnect_all(stf: STFConnect):
    """一键释放全部记录中的连接设备"""
    for device in stf.divice_dict.keys():
        if stf.divice_dict[device] not in ['0', '1']:
            if stf.remote_disconnect(stf.divice_dict[device]):
                stf.divice_dict[device] = '1'
        if stf.divice_dict[device] == '1':
            stf.remove_device(device)


if __name__ == '__main__':
    stf = STFConnect()
    while True:
        print('1.本机adb设备列表\n'
              '2.远程STF设备列表\n'
              '3.设置token\n'
              '4.设置STF地址\n'
              '5.连接全部远程STF设备\n'
              '6.断开全部已连接的STF设备\n'
              '已经连接的设备列表：' + str(stf.device_list()))
        list_selection = input('请选择你需要的操作（退出请输入exit）：')
        if list_selection == '1':
            print('本机现在连接的设备列表为：\n' + str(stf.get_adb_devices_list()))
        elif list_selection == '2':
            print('远程STF可连接的设备列表为：')
            stf_list = stf.get_stf_devices_list()
            for num, device_serial in enumerate(stf_list):
                print(str(num + 1) + '.' + str(device_serial))
            stf_selection = input('请选择你需要操作的设备序号：')
            if stf_selection == 'exit':
                break
            print('1.申请并连接设备\n'
                  '2.断开并释放设备')
            stf_selection = eval(stf_selection) - 1
            move = input('对设备' + str(stf_list[stf_selection]) + '要进行的操作是：')
            if move == 'exit':
                break
            elif move == '1':
                if not stf.add_device(stf_list[stf_selection]):
                    print('添加设备权限报错！')
                    continue
                if not stf.remote_connect(stf_list[stf_selection]):
                    stf.remove_device(stf_list[stf_selection])
                    print('申请设备连接报错！已经对设备取消权限！请重试！')
                    continue
            elif move == '2':
                if not stf.remote_disconnect(stf.divice_dict[stf_list[stf_selection]]):
                    print('adb未能断开连接！')
                    continue
                if not stf.remove_device(stf_list[stf_selection]):
                    print('远程未能释放设备！')
                    continue
        elif list_selection == '3':
            stf.set_token(input('请输入新的token值：'))
        elif list_selection == '4':
            stf.set_stf_url(input('请输入新的URL地址：'))
        elif list_selection == '5':
            connect_all_emulator(stf)
            print('全部设备已连接！')
        elif list_selection == '6':
            disconnect_all(stf)
            print('全部设备已断开！')
        elif list_selection == 'exit':
            break
