# (C) Copyright 2019 Hewlett Packard Enterprise Development LP.
# Generic Aruba Switch classes

import classes.classes
import requests
sessionid = requests.Session()

import urllib3
import json
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import pygal  
from pygal.style import BlueStyle
from pygal.style import Style

custom_style = Style(
  background='transparent',
  plot_background='transparent',
  foreground='#004d4d',
  foreground_strong='#004d4d',
  foreground_subtle='#004d4d',
  opacity='.6',
  opacity_hover='.9',
  transition='400ms ease-in',
  label_font_size=15,
  title_font_size=20,
  colors=('#E853A0', '#E8537A', '#E95355', '#E87653', '#E89B53'))

def checkifOnline(deviceid,ostype):
    # Login and logout of the device to see if the device is online
    if ostype=="arubaos-cx":
        try:
            sessionid=classes.classes.logincx(deviceid)
            if sessionid==401:
                return "Offline"
            else:
                classes.classes.logoutcx(sessionid,deviceid)
                return "Online"
        except:
            pass
    if ostype=="arubaos-switch":
        try:
            header=classes.classes.loginswitch(deviceid)
            if header==401:
                return "Offline"
            else:
                classes.classes.logoutswitch(header,deviceid)
                return "Online"
        except:
            pass
    return

def discoverModel(deviceid):
    # Performing REST calls to discover what switch model we are dealing with
    # Check whether device is ArubaOS-CX
    discoverSuccess=0
    # Check whether the device is ArubaOS-Switch by obtaining the local lldp and system information 
    try:
        header=classes.classes.loginswitch(deviceid)
        url="lldp/local_device/info"
        response =classes.classes.getRESTswitch(header,url,deviceid)
        classes.classes.logoutswitch(header,deviceid)
        if 'system_description' in response:
            # This is an ArubaOS-Switch switch. System description is a comma separated string that contains product and version information
            # Splitting the string into a list and then assign the values  
            deviceInfo=response['system_description'].split(",")
            # Obtaining system information. This information also contains port information
            url="system/status/switch"
            header=classes.classes.loginswitch(deviceid)
            sysinfo=classes.classes.getRESTswitch(header,url,deviceid)
            classes.classes.logoutswitch(header,deviceid)
            # Check whether the device is configured for VSF or BPS, or whether it's a stand alone switch. If the latter is the case, the vsf and bps fields remain empty
            if sysinfo['switch_type']=="ST_STACKED":
                url="stacking/vsf/members"
                # Getting the member information, this information contains which device is the master/commander. This is for running VSF
                header=classes.classes.loginswitch(deviceid)
                vsfinfo=classes.classes.getRESTswitch(header,url,deviceid)
                classes.classes.logoutswitch(header,deviceid)
                if 'message' in vsfinfo:
                    vsfinfo={}
                else:
                    sysinfo= {**sysinfo,**vsfinfo}
                # If there is no response, this means that the switches are running BPS
                url="stacking/bps/members"
                header=classes.classes.loginswitch(deviceid)
                bpsinfo=classes.classes.getRESTswitch(header,url,deviceid)
                classes.classes.logoutswitch(header,deviceid)
                if 'message' in bpsinfo:
                    bpsinfo={}
                else:
                    sysinfo= {**sysinfo,**bpsinfo}
                # Updating the database with all the gathered information
            queryStr="update devices set ostype='arubaos-switch', platform='{}', osversion='{}', sysinfo='{}' where id='{}'".format(deviceInfo[0],deviceInfo[1],json.dumps(sysinfo),deviceid)
            classes.classes.sqlQuery(queryStr,"update")
            discoverSuccess=1
    except:
        pass
    # Now check whether this might be an AOS-CX switch
    if discoverSuccess==0:
        try:
            url="system?attributes=platform_name%2Csoftware_version%2Csubsystems&depth=1"
            response =classes.classes.getRESTcx(deviceid,url)
            if 'platform_name' in response:
                print("This is an AOS-CX switch")
                # It is an ArubaOS-CX device. Obtain the interface information and then update the database
                try:
                    queryStr="update devices set ostype='arubaos-cx', platform='{}', osversion='{}', sysinfo='{}' where id='{}'".format(response['platform_name'], response['software_version'], json.dumps(response['subsystems']),deviceid)
                    result=classes.classes.sqlQuery(queryStr,"update")
                    discoverSuccess=1
                except:
                    print("could not store the AOS-CX information into the database")
        except:
            print("AOS-CX cannot be discovered")
    # Device has not been discovered. We have to set the ostype, platform and osversion to unknown
    if discoverSuccess==0:
        queryStr="update devices set ostype='Unknown', platform='Unknown', osversion='Unknown' where id='{}'".format(deviceid)
        classes.classes.sqlQuery(queryStr,"update")
    
def devicedbAction(formresult):
    # This definition is for all the database actions for switches, based on the user click on the pages
    queryStr="select distinct ostype from devices where ostype='arubaos-cx' or ostype='arubaos-switch' or ostype='Unknown'"
    switchos=classes.classes.sqlQuery(queryStr,"select")
    globalsconf=classes.classes.globalvars()
    queryStr="select distinct platform from devices where ostype='arubaos-cx' or ostype='arubaos-switch' or ostype='Unknown'"
    platforms=classes.classes.sqlQuery(queryStr,"select")
    searchAction="None"
    entryExists=0
    if(bool(formresult)==True): 
        if 'topology' in formresult:
            topology=1
        else:
            topology=0
        try:
            formresult['pageoffset']
            pageoffset=formresult['pageoffset']
        except:
            pageoffset=0
        if(formresult['action']=="Submit device"):
            # First check if the IP address already exists. If there is already a device with the same IP address, don't insert
            queryStr="select id from devices where ipaddress='{}'".format(formresult['ipaddress'])
            checkDuplicate=classes.classes.sqlQuery(queryStr,"selectone")
            if checkDuplicate:
                entryExists=1
            else:
                queryStr="insert into devices (description,ipaddress,username,password,cpu,memory,sysinfo,ports,interfaces,vrf,vsx,vsxlags,vsf,bps,lldp,routeinfo,topology) values ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')" \
                .format(formresult['description'],formresult['ipaddress'],formresult['username'],classes.classes.encryptPassword(globalsconf['secret_key'],formresult['password']),'','[]','[]','[]','[]','{}','{}','{}','{}','{}','{}','{}',topology)
                deviceid=classes.classes.sqlQuery(queryStr,"insert")
                # Discover what type of device this is and update the database with the obtained information
                discoverModel(deviceid)
        elif  (formresult['action']=="Submit changes"):
            # First check if the IP address already exists. If there is already a device with the same IP address, don't insert
            queryStr="select id from devices where ipaddress='{}'".format(formresult['ipaddress'])
            checkDuplicate=classes.classes.sqlQuery(queryStr,"selectone")
            # If the id result is different than the deviceid formresult, then there is already another entry with the same IP address
            if checkDuplicate:
                if str(checkDuplicate['id'])!=formresult['deviceid']:
                    entryExists=1
                else:
                    queryStr="update devices set description='{}',ipaddress='{}',username='{}',password='{}', topology='{}' where id='{}' "\
                    .format(formresult['description'],formresult['ipaddress'],formresult['username'],classes.classes.encryptPassword(globalsconf['secret_key'], formresult['password']),topology,formresult['deviceid'])
                    print(queryStr)
                    classes.classes.sqlQuery(queryStr,"update")
                    # Discover what type of device this is and update the database with the obtained information
                    discoverModel(formresult['deviceid'])
            else:
                queryStr="update devices set description='{}',ipaddress='{}',username='{}',password='{}', topology='{}' where id='{}' "\
                .format(formresult['description'],formresult['ipaddress'],formresult['username'],classes.classes.encryptPassword(globalsconf['secret_key'], formresult['password']),topology,formresult['deviceid'])
                print(queryStr)
                classes.classes.sqlQuery(queryStr,"update")
                # Discover what type of device this is and update the database with the obtained information
                discoverModel(formresult['deviceid'])
        elif (formresult['action']=="Delete"):
            # Delete from the topology table, if entries exist
            queryStr="select ipaddress from devices where id='{}'".format(formresult['deviceid'])
            result=classes.classes.sqlQuery(queryStr,"selectone")
            queryStr="delete from topology where switchip='{}'".format(result['ipaddress'])
            classes.classes.sqlQuery(queryStr,"delete")
            # Delete from the devices table
            queryStr="delete from devices where id='{}'".format(formresult['deviceid'])
            classes.classes.sqlQuery(queryStr,"delete")
        try:
            searchAction=formresult['searchAction']
        except:
            searchAction=""    
        if formresult['searchIPaddress'] or formresult['searchDescription'] or formresult['searchVersion'] or formresult['searchPlatform'] or formresult['searchOS'] or formresult['searchTopology']:
            constructQuery= " where (ostype='arubaos-cx' or ostype='arubaos-switch' or ostype='Unknown') AND "
        else:
            constructQuery="where (ostype='arubaos-cx' or ostype='arubaos-switch' or ostype='Unknown')      "
        if formresult['searchDescription']:
            constructQuery += " description like'%" + formresult['searchDescription'] + "%' AND "
        if formresult['searchVersion']:
            constructQuery += " osversion like '%" + formresult['searchVersion'] + "%' AND "
        if formresult['searchIPaddress']:
            constructQuery += " ipaddress like'%" + formresult['searchIPaddress'] + "%' AND "
        if formresult['searchPlatform']:
            constructQuery += " platform like'%" + formresult['searchPlatform'] + "%' AND "
        if formresult['searchTopology']:
            constructQuery += " topology='" + formresult['searchTopology'] + "' AND "
        if formresult['searchOS']:
            constructQuery += " ostype like'%" + formresult['searchOS'] + "%' AND "

        # We have to construct the query based on the formresult information (entryperpage, totalpages, pageoffset)
        queryStr="select COUNT(*) as totalentries from devices " + constructQuery[:-4]
        navResult=classes.classes.navigator(queryStr,formresult)

        totalentries=navResult['totalentries']
        entryperpage=navResult['entryperpage']
        # If the entry per page value has changed, need to reset the pageoffset
        if formresult['entryperpage']!=formresult['currententryperpage']:
            pageoffset=0
        else:
            pageoffset=navResult['pageoffset']
        # We have to construct the query based on the formresult information (entryperpage, totalpages, pageoffset)
        queryStr = "select * from devices " + constructQuery[:-4] + " LIMIT {} offset {}".format(entryperpage,pageoffset)
        result=classes.classes.sqlQuery(queryStr,"select")
    else:
        queryStr="select COUNT(*) as totalentries from devices where (ostype='arubaos-cx' or ostype='arubaos-switch' or ostype='Unknown')"
        navResult=classes.classes.sqlQuery(queryStr,"selectone")
        entryperpage=10
        pageoffset=0
        queryStr="select id, description, ipaddress, username, password, ostype, platform, osversion, topology from devices where ostype='arubaos-cx' or ostype='arubaos-switch' or ostype='Unknown' LIMIT {} offset {}".format(entryperpage,pageoffset)
        result=classes.classes.sqlQuery(queryStr,"select")
    return {'result':result, 'switchos': switchos, 'platforms': platforms, 'totalentries': navResult['totalentries'], 'pageoffset': pageoffset, 'entryperpage': entryperpage,'entryExists': entryExists}


def interfacedbAction(deviceid, interface,ostype):
    # Definition that obtains all the relevant information from the database for showing on the html pages
    queryStr="select sysinfo,interfaces, lldp from devices where id='{}'".format(deviceid)
    result=classes.classes.sqlQuery(queryStr,"selectone")
    interfaceinfo=json.loads(result['interfaces'])
    if ostype=="arubaos-switch" and interfaceinfo:
        lldpinfo=json.loads(result['lldp'])
    else:
        lldpinfo={}
    sysinfo=json.loads(result['sysinfo'])
    if ostype=="arubaos-cx":
        # extract the selected interface information
        for items in interfaceinfo:
            if items['name']==interface:
                # Assign the selected interface values
                interfaceinfo=items
    elif ostype=="arubaos-switch":
        # Obtain information of the selected interface
        if interfaceinfo:
            for items in interfaceinfo['port_statistics_element']:
                if items['id']==interface:
                    interfaceinfo=items
            for items in sysinfo['blades']:
                for hwitems in items['data_ports']:
                    if hwitems['port_name']==interface:
                        interfaceinfo= {**interfaceinfo,**hwitems}
        # Obtain lldp information from the selected interface
        if interface == "0":
            lldpinfo={}
        else:
            if lldpinfo:
                for items in lldpinfo['lldp_remote_device_element']:
                    if items['local_port']==interface:
                        lldpinfo=items
                    else:
                        pass
            else:
                lldpinfo={}
    return (interfaceinfo,lldpinfo)

def showLinechart(deviceid,entity,ostype,stacktype,title):
    # definition that obtains the information from the database and formats this to display a linechart
    dataset=[]
    # Obtaining the relevant data (CPU or Memory) from the database as dataset value.
    queryStr="select {} as dataset from devices where id={}".format(entity,deviceid)
    result=classes.classes.sqlQuery(queryStr,"selectone")
    dataset=json.loads(result['dataset'])
    # Based on the ostype value, the Y-title has to be different for the memory. In ArubaOS-CX the memory usage is displayed and in ArubaOS-Switch the available memory
    if ostype=="arubaos-cx":
        y_title="%"
    elif ostype=="arubaos-switch":
        # If the device is running VSF or BPS we have to provide some additional information to the getCPU and getMemory definitions
        if entity=='memory':
            y_title="Bytes"
        else:
            y_title="%"
    xlabel = []
    values = []
    # Creating the datasets for the linechart
    for items in dataset:
        xlabel.append(items[0])
        values.append(int(items[1]))
    line_chart = pygal.Line(style=custom_style, show_legend=False, y_title=y_title, x_label_rotation=80)
    line_chart.title = title
    line_chart.x_labels = map(str, xlabel)
    line_chart.add('', values)
    return line_chart

def portAccess(deviceid):
    #Show access port security
    try:
        header=classes.classes.loginswitch(deviceid)
        url="monitoring/port-access/clients/detailed"
        response =classes.classes.getRESTswitch(header,url,deviceid)
        classes.classes.logoutswitch(header,deviceid)
    except:
        response={}
    return response

def clearClient(deviceid,macaddress,port,authmethod):
    # based on the authentication method, push reset client
    result=""
    if authmethod=="macauth":
        cmd="aaa port-access mac-based " + port + " reauthenticate mac-addr " + macaddress
        result=classes.classes.anycli(cmd,deviceid)
    elif authmethod=="dot1x":
        # cmd="aaa port-access authenticator " + port + " reauthenticate"
        cmd="interface " + port + " disable"
        result=classes.classes.anycli(cmd,deviceid)
        cmd="interface " + port + " enable"
        result=classes.classes.anycli(cmd,deviceid)
    return result
