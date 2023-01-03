# Copyright (c) 2022, Hans kim

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
# CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os, time, sys
import json
from functions_s import (configVars, dbconMaster, checkAuthMode, modifyConfig, is_online, message, TZ_OFFSET, log)

MYSQL = { 
    "commonParam": configVars('software.mysql.db') + "." + configVars('software.mysql.db_common.table.param'),
    "commonSnapshot": configVars('software.mysql.db') + "." + configVars('software.mysql.db_common.table.snapshot'),
    "commonCounting": configVars('software.mysql.db') + "." + configVars('software.mysql.db_common.table.counting'),
    "commonHeatmap": configVars('software.mysql.db') +"." + configVars('software.mysql.db_common.table.heatmap'),
    "commonCountEvent": configVars('software.mysql.db') + "." + configVars('software.mysql.db_common.table.count_event'),
    "commonFace": configVars('software.mysql.db') + "." + configVars('software.mysql.db_common.table.face'),
    "customCamera": "camera",
    "customCounterLabel": "counter_label",
    "customRtCount": "realtime_screen",
}

# TZ_OFFSET =  configVars('system.datetime.timezone.offset')
# try :
#     TZ_OFFSET = int(TZ_OFFSET)

# except:
#     TZ_OFFSET = 0

# if not TZ_OFFSET:
#     TZ_OFFSET = 3600*8


def getWriteParam(device_info):
    arr_cmd = []
    dbconn0 = dbconMaster()
    with dbconn0:
        cur = dbconn0.cursor()    
        sq = "select write_cgi_cmd from " + MYSQL['commonParam'] + " where device_info = '%s' and write_cgi_cmd is not null and write_cgi_cmd != '' limit 1 " %device_info
        cur.execute(sq)
        row = cur.fetchone()
    
        if row:
            arr_cgi_cmd = row[0].splitlines()
            for cgi_cmd in arr_cgi_cmd:
                if not cgi_cmd.strip():
                    continue
                arr_cmd.append(cgi_cmd.strip())
    
    return arr_cmd

def putWriteParam(device_info, arr_cmd=[]):
    cmd = '\n'.join(arr_cmd)
    dbconn0 = dbconMaster()
    with dbconn0:
        cur = dbconn0.cursor() 
        sq = "update " + MYSQL['commonParam'] + " set write_cgi_cmd='%s' where device_info = '%s' " %(cmd, device_info)
        print(sq)
        # cur.execute(sq)
        # dbconn0.commit()
        cur.close()

    return True


def updateSimpleParam(device_info, usn, url):
    # device_info, usn, url only. for browsing devices
    regdate = time.strftime("%Y-%m-%d %H:%M:%S")
    dbconn0 = dbconMaster()
    with dbconn0:
        cur = dbconn0.cursor()
        sq = "select pk, url from " + MYSQL['commonParam'] + " where device_info=%s" 
        cur.execute(sq, device_info)
        rowa = cur.fetchone()

        sq = "select pk from " + MYSQL['commonSnapshot'] + " where device_info=%s"
        cur.execute(sq, device_info)
        rowb = cur.fetchone()

        if not rowa:
            sq = "insert into " + MYSQL['commonParam'] + "(device_info, usn, url, initial_access) values(%s, %s, %s, %s)" 
            cur.execute(sq, (device_info, usn, url, regdate))
        elif url != rowa[1]:
            sq = "update " + MYSQL['commonParam'] + " set url=%s where device_info=%s"
            cur.execute(sq, (url, device_info) )
            
        if not rowb:
            sq = "insert into " + MYSQL['commonSnapshot'] + "(device_info, regdate) values(%s, %s)"
            cur.execute(sq, (device_info, regdate))  
        dbconn0.commit()
    return True

def updateParam(device_info='', param ={}) :
    regdate = time.strftime("%Y-%m-%d %H:%M:%S")
    print ("updateing param from %s at %s to DB" %(device_info, regdate))

    if not param['ret'] :
        log.error("Retrieve Param faild from %s at %s" %(device_info, regdate))
        return False

    if not device_info:
        device_info = "mac=%s&brand=%s&model=%s" %(param['mac'], param['brand'], param['model'])
    
    dbconn0 = dbconMaster()
    with dbconn0:
        cur = dbconn0.cursor()
        sq = "select pk, method from " + MYSQL['commonParam'] + " where device_info = %s limit 1" 
        cur.execute(sq, device_info)
        row = cur.fetchone()
        if not row : # new device
            if len(param['usn']) >9:
                param['usn'] = param['usn'][:9]
            sq = "insert into " + MYSQL['commonParam'] + "(device_info, initial_access, usn, product_id) values(%s, %s, %s, %s)"
            cur.execute(sq, (device_info, regdate, param['usn'], param['productid']))
            dbconn0.commit()

            sq = "select pk, method from " + MYSQL['commonParam'] + " where device_info = %s limit 1" 
            cur.execute(sq, device_info)
            row = cur.fetchone()

        sq = "update " + MYSQL['commonParam'] + " set product_id=%s, lic_pro=%s, lic_surv=%s, lic_count=%s, heatmap=%s, countrpt=%s, face_det=%s, macsniff=%s, param=%s, last_access=%s where device_info=%s" 

        cur.execute(sq, (param['productid'], param['lic_pro'], param['lic_surv'], param['lic_count'], param['heatmap'], param['countrpt'], param['face_det'], param['macsniff'], param['param'], regdate, device_info))

        if row[1] == 'auto':
            sq = "update " + MYSQL['commonParam'] + " set url=%s where device_info=%s "
            cur.execute(sq, (param['url'], device_info))

        dbconn0.commit()
        # log.info ("%s update param OK" %device_info)
        # print ("update params from %s at %s" %(device_info, regdate))
 
    return param


def updateSnapshot(device_info='', snapshot=''):
    regdate = time.strftime("%Y-%m-%d %H:%M:%S")
    strn = "updating snapshot from %s at %s to DB" %(device_info, regdate)
    message(strn)
    log.info(strn)
 
    record = [snapshot, regdate]
    dbconn0 = dbconMaster()
    with dbconn0:
        cur = dbconn0.cursor()
        sq = "select pk from  " + MYSQL['commonSnapshot'] + " where device_info = '%s' order by pk desc limit 1" %(device_info)
        cur.execute(sq)
        row = cur.fetchone()

        if row:
            sq = "update " + MYSQL['commonSnapshot'] + " set body=%s, regdate=%s where pk=%s " 
            record.append(row[0])

        else:
            sq = "insert into " + MYSQL['commonSnapshot'] + "(body, regdate, device_info) values(%s, %s, %s)" 
            record.append(device_info)
        record = tuple(record)
        cur.execute(sq, record)
        dbconn0.commit()
    log.info("%s: snapshot updated" %device_info)
    return True    

def getLatestTimestamp(table, device_info):
    dbconn0 = dbconMaster()
    with dbconn0:
        cur = dbconn0.cursor()
        sq = "select timestamp from %s where device_info='%s' order by timestamp desc limit 1 " %(table, device_info)
        cur.execute(sq)
        row = cur.fetchone()
        # from_t = time.strftime("%Y/%m/%d%%20%H:%M", time.gmtime(row[0])) #count
        # from_t = time.strftime("%Y/%m/%d%%20%H:%M", time.gmtime(row[0]+3600)) #heatmap
        if row :
            from_t = time.strftime("%Y/%m/%d%%20%H:%M", time.gmtime(row[0]))
            readflag = int(time.time()) + TZ_OFFSET - int(row[0])
            ts = int(row[0])

        else :
            from_t = "2018/11/12%2000:00"
            readflag = 115200
            ts = 0
        return from_t, readflag, ts


def updateCountingReport(device_info='', arr_record=[]):
    regdate = time.strftime("%Y-%m-%d %H:%M:%S")
    strn =  "updating counting report from %s at %s to DB" %(device_info, regdate)
    message(strn)
    log.info(strn)
   
    dbconn0 = dbconMaster()
    with dbconn0:
        cur = dbconn0.cursor()
        for record_dict in arr_record:
            sq = "select pk from " + MYSQL['commonCounting'] + " where timestamp < %d and flag='y' order by timestamp asc limit 1" %(int(time.time()) - int(configVars('software.mysql.recycling_time')))

            cur.execute(sq)
            rowa = cur.fetchone()
            record = [device_info, regdate, record_dict['timestamp'], record_dict['datetime'], record_dict['ct_name'], record_dict['ct_value']]

            if rowa:
                record.append(rowa[0])
                sq = "update " + MYSQL['commonCounting'] + " set device_info= %s, regdate=%s, timestamp = %s, datetime= %s, counter_name= %s, counter_val= %s, flag='n' where pk = %s" 

            else:
                sq = "insert into " + MYSQL['commonCounting'] + "(device_info, regdate, timestamp, datetime, counter_name, counter_val) values(%s, %s, %s , %s, %s, %s)" 

            # print (sq, record)
            cur.execute(sq, tuple(record))
        
        log.info( "%s:%s:%d updated" %(device_info, MYSQL['commonCounting'], len(arr_record)))
		
        dbconn0.commit()
    return True          

def updateHeatmap(device_info='', arr_record=[]):
    regdate = time.strftime("%Y-%m-%d %H:%M:%S")
    strn = "updating heatmap reports from %s at %s to DB" %(device_info, regdate)
    message(strn)
    log.info(strn)

    dbconn0 = dbconMaster()
    with dbconn0:      
        cur = dbconn0.cursor()
        # for record in arr_record:
        for record_dict in arr_record:
            sq = "select pk from " + MYSQL['commonHeatmap'] + " where timestamp < %d and flag = 'y' order by timestamp asc limit 1 " %(int(time.time()) - int(configVars('software.mysql.recycling_time'))) 
            cur.execute(sq)
            rowa = cur.fetchone()

            record = [device_info, regdate, record_dict['timestamp'], record_dict['datetime'], record_dict['heatmap']]
            if rowa:
                record.append(rowa[0])
                sq = "update " + MYSQL['commonHeatmap'] + " set device_info=%s, regdate=%s, timestamp=%s, datetime=%s, body_csv=%s, flag='n' where pk =%s"
            else :
                sq = "insert into " + MYSQL['commonHeatmap'] + "(device_info, regdate, timestamp, datetime, body_csv)  values(%s, %s, %s, %s, %s)"
        	
            record = tuple(record)
            # print (sq, record)
            cur.execute(sq, record)

        log.info( "%s:%s:%d updated" %(device_info, MYSQL['commonHeatmap'], len(arr_record)))
        dbconn0.commit()

    return True   

def getDeviceListFromDB():
    arr_dev = []
    arr_rs = []
    nums_online=0

    dbconn0 = dbconMaster()
    with dbconn0:
        cur = dbconn0.cursor()
        sq = "select pk, device_info, url, user_id, user_pw from " + MYSQL['commonParam'] + " order by last_access desc limit 250"
        cur.execute(sq)
        rows = cur.fetchall()
        
        for row in rows:
            arr_rs.append(row)

        modifyConfig('software.status.connecting_device', len(arr_dev))

    for dev in arr_rs:
        pk, device_info, dev_ip, user_id, user_pw = dev
        if is_online(dev_ip):
            online = True
            nums_online += 1
            authkey, devfamily = checkAuthMode(dev_ip, user_id, user_pw )
        else :
            online = False
            authkey, devfamily = "", ""
       
        arr_dev.append({
            "device_info": device_info,
            "ip": dev_ip,
            "user_id": user_id,
            "user_pw": user_pw,
            "online": online,
            "authkey": authkey,
            "device_family": devfamily
        })
    modifyConfig('software.status.active_device', nums_online)
    return arr_dev

def getDeviceInfoFromDB(device_info):
    dbconn0 = dbconMaster()
    with dbconn0:
        cur = dbconn0.cursor()
        sq = "select pk, db_name, heatmap, countrpt from " + MYSQL['commonParam'] + " where device_info=%s" 
        # print sq
        cur.execute(sq, device_info)
        row = cur.fetchone()
        pk, db_name, heatmap, countrpt =  row
    if pk:
        return {"db_name": db_name, "heatmap": heatmap, "countrpt": countrpt}
    return False



def updateFaceThumnmail(face_dict):
    regdate =  time.strftime("%Y-%m-%d %H:%M:%S")
    dbconn0 = dbconMaster()
    with dbconn0:
        cur = dbconn0.cursor()
        sq = "select device_info from " +  MYSQL['commonParam'] + " where usn=%s and (product_id=%s or url=%s)"
        cur.execute(sq, (face_dict['usn'], face_dict['productid'], face_dict['ip']) )
        row = cur.fetchone()
        if not row :
            msg =  "usn:%s, ip:%s, productid:%s, Device is not registerd" %(face_dict['usn'], face_dict['ip'], face_dict['productid'])
            print (msg)
            log.error(msg)
            return False

        deviceinfo = row[0]
        sq = "select pk from " + MYSQL['commonFace'] + " where (flag = 'n') or (flag_fd='y' and  flag_ud='y' and timestamp < %d) order by timestamp asc limit 1 " %(int(time.time()) - int(configVars('software.mysql.recycling_time'))) 
        cur.execute(sq)
        row = cur.fetchone()

        record = [deviceinfo, regdate, face_dict['timestamp'], face_dict['datetime'], face_dict['img_b64'], face_dict['getstr'][:255], face_dict['eventinfo'][:255]]
        if row:
            record.append(row[0])
            sq = "update " + MYSQL['commonFace'] + " set device_info=%s, regdate=%s, timestamp=%s, datetime=%s, thumbnail=%s, get_str=%s, event_info=%s, age=0, gender='', face_token='',flag = 'y', flag_fd='n', flag_ud='n', flag_fs='n' where pk=%s" 
        else :
            sq = "insert into " + MYSQL['commonFace'] + "(device_info, regdate, timestamp, datetime, thumbnail, get_str, event_info, flag) values(%s, %s, %s, %s, %s, %s, %s, 'y')" 

        log.info(deviceinfo + ": Get Thumnail")
        cur.execute(sq, tuple(record))
        dbconn0.commit()

# def getRtCounting(cursor, db_name, counters, ct_labels):
#     ct_mask = list()
#     arr_t = list()
#     arr_rs = dict()
#     arr_rs_y = dict()
#     arr_f = set()

#     for day in counters:
#         for ct_label in counters[day]:
#             if ct_label in ct_labels:
#                 if day == 'today':
#                     ct_mask.append("(counter_label='%s' and timestamp>%d)" %(ct_label, counters['today'][ct_label]['latest']))
#                     arr_rs[ct_label] =  {"start":0, "end":0, "rtcount":0,  "count":0}
#                 if day == 'yesterday':
#                     arr_rs_y[ct_label] =  {"start":0, "end":0, "rtcount":0,  "count":counters['yesterday'][ct_label]['count']}
#     # print(arr_rs)
#     sq_s = ""
#     if (ct_mask) :
#         sq_s = ' or '.join(ct_mask)
#         sq_s = ' and (%s)' %(sq_s)
#     sq = "select timestamp, counter_val, device_info, counter_label, counter_name from common.counting_event where db_name='%s' %s  order by timestamp asc" %(db_name, sq_s) 
#     # print (sq)

#     cursor.execute(sq)
#     for row in cursor.fetchall():
#         arr_t.append({
#             "timestamp": row[0],
#             "count": row[1],
#             "device_info": row[2],
#             "ct_label": row[3],
#             "ct_name": row[4]
#         })
#     # for r in arr_t:
#     #     print(r)
#     for assoc in arr_t:
#         label = "%s&%s&%s" %(assoc['device_info'], assoc['ct_label'], assoc['ct_name'])
#         if not (label in arr_f) :
#             arr_f.add(label)
#             arr_rs[assoc['ct_label']]["start"] += assoc['count']
#     arr_t.reverse()
#     arr_f.clear()
#     for assoc in arr_t:
#         label = "%s&%s&%s" %(assoc['device_info'], assoc['ct_label'], assoc['ct_name'])
#         if not (label in arr_f) :
#             arr_f.add(label)
#             arr_rs[assoc['ct_label']]["end"] += assoc['count']
    
#     for ct_label in counters['today']:
#         if ct_label in ct_labels:
#             arr_rs[ct_label]["rtcount"] = arr_rs[ct_label]["end"] - arr_rs[ct_label]["start"]
#             arr_rs[ct_label]["count"] = counters['today'][ct_label]['count'] + arr_rs[ct_label]["rtcount"]

#     # print(arr_rs)
#     return {'today': arr_rs, 'yesterday': arr_rs_y}


# def updateRtCounting(dbconn0, db_name):
#     ts = time.time()
#     ct_labels = set()
#     counters = {"today":{}, "yesterday":{}}
#     arr_number = list()
#     cur = dbconn0.cursor()

#     sq = "select pk, category, name, ct_labels, rule, text, position from %s.%s where enable='yes' and (name like 'number%%' or category='crpt') " %(db_name, MYSQL['customRtCount'])
#     cur.execute(sq)
#     for row in cur.fetchall():
#         if row[2].startswith('number'):
#             for c in json.loads(row[3]):
#                 ct_labels.add(c)
#             arr_number.append({
#                 "pk": row[0],
#                 "name": row[2],
#                 "labels": json.loads(row[3]),
#                 "rule": row[4]
#             })
#         elif row[1] == 'crpt':
#             day = "today" if int(row[2]) == 0 else "yesterday"
#             counters[day][row[3]] = {
#                 "count": int(row[5]),
#                 "latest": int(row[6]),
#             }
#     # print("ct_labels", ct_labels)
#     # print("numbers", arr_number)
#     # print("counters", counters)
    
#     rt_counting = getRtCounting(cur, db_name, counters, ct_labels)
#     arr_sq = list()
#     operator = ['+', '-', '/']
#     for day in rt_counting:
#         for assoc in arr_number:
#             # print (day, rt_counting[day], assoc)
#             if day == assoc['rule']:
#                 sq = "update %s.realtime_screen set text='%d' where pk=%d" %(db_name, rt_counting[day][assoc['labels'][0]]['count'], assoc['pk'])
#                 arr_sq.append(sq)
#             elif day=='today':
#                 for op in operator:
#                     ex = assoc['rule'].split(op)
#                     if len(ex) == 2:
#                         if op == '+':
#                             num = rt_counting['today'][ex[0]]['count'] + rt_counting['today'][ex[1]]['count']
#                         elif op == '-':
#                             num = rt_counting['today'][ex[0]]['count'] - rt_counting['today'][ex[1]]['count']
#                         elif op == '/':
#                             num = rt_counting['today'][ex[0]]['count'] / rt_counting['today'][ex[1]]['count']
#                         else :
#                             continue
#                         sq = "update %s.realtime_screen set text='%d' where pk=%d" %(db_name, num, assoc['pk'])
#                         arr_sq.append(sq)
    
#     for sq in arr_sq:
#         print (sq)
#         cur.execute(sq)
#     dbconn0.commit()
#     print ("getRtCounting", time.time()-ts)        


def updateEventCount(event_rs):
    dbconn0 = dbconMaster()
    with dbconn0:
        cur = dbconn0.cursor()
        sq = "select device_info, db_name from " + MYSQL['commonParam'] + " where url=%s "
        cur.execute(sq, event_rs['ip'])
        deviceinfo, db_name = cur.fetchone()
        if db_name == 'none' or not db_name:
            return False
        sq = "select A.counter_label from %s.%s as A inner join %s.%s as B on A.camera_code=B.code where A.counter_name='%s' and B.device_info='%s'"  %(db_name, MYSQL['customCounterLabel'], db_name, MYSQL['customCamera'], event_rs['ct_name'], deviceinfo)
        # print (sq)
        cur.execute(sq)
        ct_label = cur.fetchone()[0]
        record = [event_rs['ip'], deviceinfo, time.strftime("%Y-%m-%d %H:%M:%S"), event_rs['timestamp'], event_rs['ct_name'], event_rs['ct_val'], event_rs['getstr'][:255], db_name, ct_label]

        sq = "select pk from " + MYSQL['commonCountEvent'] + "  where timestamp < %s order by timestamp asc limit 1 "
        cur.execute(sq, (int(time.time()) - int(configVars('software.mysql.recycling_time'))) )
        row = cur.fetchone()
        if row:
            record.append(row[0])
            sq = "update " + MYSQL['commonCountEvent'] + " set device_ip=%s, device_info=%s, regdate=%s, timestamp=%s, counter_name=%s, counter_val=%s, message=%s, flag='y', status=0, db_name=%s, counter_label=%s where pk = %s"
        else:
            sq = "insert into " + MYSQL['commonCountEvent'] + "(device_ip, device_info, regdate, timestamp, counter_name, counter_val, message, flag, status, db_name, counter_label)  values(%s, %s, %s, %s, %s, %s, %s, 'y', 0, %s, %s) "
        # print (sq, tuple(record))
        cur.execute(sq, tuple(record))
        # log.info("count Event %s, %s, %s, %s, %s, %s" %(tuple(record[:6])))
        # updateRtCounting(dbconn0, db_name)
        dbconn0.commit()



if __name__ == '__main__':
    # x = getLatestTimestamp( MYSQL['commonCounting'], 'mac=001323A00326&brand=CAP&model=NS602HD' )
    # print(x)
    # x = getLatestTimestamp( MYSQL['commonHeatmap'], 'mac=001323A00326&brand=CAP&model=NS602HD' )
    # print(x)
    # x = getDeviceListFromDB()
    # for xx in x:
    #     print(xx)
    # dbconn0 = dbconMaster()
    # with dbconn0:    
    #     updateRtCounting(dbconn0, 'cnt_demo')

    sys.exit()