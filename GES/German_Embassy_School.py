"""
Copyright (c) 2021 Cisco Systems, Inc.

Purpose:
   Get the location of a connected endpoint

Author:
   Danmu Wu (danmwu@cisco.com)

Description:
   As per the request of customer - Beijing German Embassy School, I developped
   this script to help customer find out the location where a given endpoint
   connect to the network
"""

import sys
import pandas
import re
from netmiko import ConnectHandler
import telnetlib
import time

def main(devlistfile):
	# Read devices list from excel file
	try:
		df = pandas.read_excel(open(devlistfile,'rb'))
	except:
		print("Something went wrong when opening the DevList file.")
		sys.exit()
	
	# Fetch data and convert
	nmkch_temp = {'device_type': 'cisco_ios', 'host' : '', 'username' : '', 'password' : ''}
	devArr = df.to_numpy()
	devLi = []
	devArrLi = []
	for i in devArr:
		devLi.append(i[0])
		devArrLi.append(i.tolist())
	devLiNew = []
	for i in devArrLi:
		sshch = nmkch_temp.copy()
		sshch['host'] = i[1]
		sshch['username'] = i[4]
		sshch['password'] = i[5]
		devinfo = {}
		devinfo['devname'] = i[0]+'_'+i[1]
		devinfo['access'] = i[3]
		devinfo['port'] = i[2]
		devinfo['sshch'] = sshch
		devLiNew.append(devinfo)
	devList = dict(zip(devLi, devLiNew))

	# Ask for the mac address of which user want to search in the network
	isMac = False
	retry = 5
	while isMac==False:
		if retry>0:
			hostMac = input("Please enter the Mac Address of Host (Format xx:xx:xx:xx:xx:xx): ")
			isMac = isValidMac(hostMac)
			retry -= 1
		else:
			print("Error: Too many attempts!!")
			sys.exit()
	hostMac = macConvert(hostMac)
	print('-------------------------------------------------------------------------------------------')
	print('Now start to look for '+hostMac)
	print('-------------------------------------------------------------------------------------------')

	# Search for the host
	isFound = False
	cmd = 'show mac address-table | in ' + hostMac
	for dev in devLi:
		# connect to device and run the command - 0000.0c9f.acc7
		print('Checking on '+devList[dev]['devname']+' ...')
		if devList[dev]['access'].lower() == "ssh":
			try:
				netcon = ConnectHandler(**devList[dev]['sshch'])
				output = netcon.send_command(cmd)
				netcon.disconnect()
				if isValideOP(output):
					op = output.strip().split()
					vlan = op[0]
					macadd = op[1]
					mactype = op[2]
					port = op[3]
					print('-------------------------------------------------------------------------------------------')
					print("Host is found in Vlan "+vlan+" from "+devList[dev]['devname']+"'s interface "+port+" !\n")
					print('Output is displayed here:')
					print(cmd)
					print(output)
					print('-------------------------------------------------------------------------------------------\n\n')
					isFound = True
				else:
					print('Host is not found.\n\n')
			except Exception as e:
				print('\nFailed to connect and run command on device - ' + devList[dev]['devname']+'\n')
				print('Exception is: ')
				print(e)
		elif devList[dev]['access'].lower() == "telnet":
			wait_time = 3
			try:
				with telnetlib.Telnet(host = devList[dev]['sshch']['host'], port = devList[dev]['port'], timeout = 30) as tn:
					times = 5
					interval = 2
					while times != 0:
						time.sleep(interval)
						op = tn.read_very_eager()
						if op == b'':
							times -= 1
						else:
							if 'User' in op.decode():
								tn.write(devList[dev]['sshch']['username'].encode('ascii') + b"\n")
								time.sleep(interval)
								op = tn.read_some()
								times = 5
							if 'Password' in op.decode():
								tn.write(devList[dev]['sshch']['password'].encode('ascii') + b"\n")
								time.sleep(interval)
								op = tn.read_very_eager()
								times = 5
							if dev+'#' in op.decode():
								tn.write(cmd.encode('ascii') + b"\n")
								time.sleep(10)
								output = tn.read_very_eager().decode().split('\r\n')
								if isValideOP(output[1]):
									op = output[1].strip().split()
									vlan = op[0]
									macadd = op[1]
									mactype = op[2]
									port = op[3]
									print('-------------------------------------------------------------------------------------------')
									print("Host is found in Vlan "+vlan+" from "+devList[dev]['devname']+"'s interface "+port+" !")
									print('Output is displayed here:')
									for i in output:
										print(i)
									print('-------------------------------------------------------------------------------------------\n\n')
									isFound = True
								else:
									print('Host is not found.\n\n')
								break
					else:
						print('Failed to login '+devList[dev]['devname']+' via Telnet!\n\n')
					#'''
			except Exception as e:
				print('\nFailed to connect and run command on device - ' + devList[dev]['devname']+'\n')
				print('Exception is: ')
				print(e)
		else:
			print('\nThe script only supports SSH(default port) and Telnet connection today.  Please manually check on '+devList[dev]['devname']+' .\n')

	# Display
	if isFound == False:
		print('-------------------------------------------------------------------------------------------')
		print('Host is not found in your network!')
		print('-------------------------------------------------------------------------------------------')

def isValidIp(ip):
    if re.match(r"^\s*\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s*$", ip): return True
    return False
    
def isValidMac(mac):
    if re.match(r"^\s*([0-9a-fA-F]{2,2}:){5,5}[0-9a-fA-F]{2,2}\s*$", mac): return True
    return False

def isValideOP(str):
	if re.match(r"^ *\d{1,4} +([0-9a-fA-F]{4}\.){2}[0-9a-fA-F]{4} +[a-zA-Z]+ +[0-9a-zA-Z\/]+ *$", str): return True
	return False

def macConvert(mac):
	# currently the mac address format used to display in Cisco Catalyst9k platform is h.h.h
	mac = mac.lower()
	mac_list = mac.split(':')
	newmac = ''
	for i in range(0,len(mac_list)):
		if i%2 == 1 or i == 0:
			newmac += mac_list[i]
		else:
			newmac += '.'+mac_list[i]
	return newmac


if __name__ == '__main__':
	dev_list_path = "/yourpath/DeviceList.xls"
	main(dev_list_path)
