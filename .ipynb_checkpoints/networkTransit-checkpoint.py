'''
module networkTransit
Author: David James, 20200226, davidabraham@ucla.edu
functions:
    - mp_transitDriver
    - mp_transitTime
'''
import requests
import pandas as pd
import multiprocessing as mp
import datetime as dt
import logging as lg

'''
function mp_transitDriver
A function designed to run mp_transitTime when given a set
of data to process.
@param: DataFrame(
           Series, data['Trip ID']    - int,   Unique ID code for trip
           Series, data['Source Lat'] - float, source latitude
           Series, data['Source Lon'] - float, source longiutde
           Series, data['Dest Lat']   - float, destination latitude
           Series, data['Dest Lon']   - float, destination longitude
           Series, data['time']       - str,   time to arrive by the destination
                                        format can be 15:42:1 or 3.42pm
           Series, data['date']       - str,   date of the trip
                                        format can be 11/12/18 or 11-12-18)
@return: NONE
'''
def mp_transitDriver(data):
    lg.basicConfig(format='%(asctime)s %(message)s')

    keys = data.keys()

    cores = mp.cpu_count()
    rows = data.shape[0]
    group = rows // cores

    mpCount = [(group*i,group*(i+1),keys,data) if i < cores-1
               else (group*i,rows,keys,data)
               for i in range(cores)]
    pool = mp.Pool(cores)

    lg.info('Started processing')

    results = pool.map(mp_transitTime,mpCount)

    lg.info('Finished processing')

    df = pd.concat([pd.DataFrame(d) for d in results],ignore_index=True)
    pool.close()

    now = dt.datetime.now().strftime("%Y%m%d-%H%M")
    df.to_csv(now + 'transitTimes.csv',index=False)

'''
function mp_transitTime
A function that makes calls to the OTP server and collects its responses
@param: tuple(
          int,index[0] - starting index
          int,index[1] - ending index)
@return: DataFrame(
            Series, 'Trip ID'                    - int,   unique ID for the trip
            Series, 'Duration (min)'             - int,   duration of the entire trip in minutes
            Series, 'Walking Time (min)'         - int,   portion of the trip that is walking in minutes
            Series, 'Transit Time (min)'         - int,   portion of the trip that is on transit in minutes
            Series, 'Walking Distance (Mi)/ MAX' - float, the walking distance required to/from bus stops
            Series, 'Transfers'                  - int,   number of transfers taken between transit options
            Series, 'Message'                    - str,   message saying if a trip was found or not)
'''
def mp_transitTime(index):
    # 805, 3220, 8047
    MAXW = 805
    cols = ['Trip ID','Duration (min)','Walking Time (min)','Transit Time (min)',
            'Walking Distance (Mi)/ MAX: {0:1.1f} (Mi)'.format(MAXW/1609),
            'Transfers','Message']
    responses = {cols[0]:[],cols[1]:[],cols[2]:[],
                 cols[3]:[],cols[4]:[],cols[5]:[],cols[6]:[]}
    worker = mp.current_process()
    wid = worker.name
    keys = index[2]
    data = index[3]
    l = len(keys)

    for i in range(index[0],index[1]):
        # collecting values
        vals = []
        for j in range(l):
            vals.append(data[keys[j]][i])

        # url for calling the server
        localhost = 'http://127.0.0.1:8080/otp/routers/default/'
        url = localhost + 'plan?'
        url += 'fromPlace={0},{1}'.format(vals[1],vals[2])
        url += '&toPlace={0},{1}'.format(vals[3],vals[4])
        url += '&time={0}'.format(vals[5])
        url += '&date={0}'.format(vals[6])
        url += '&mode=TRANSIT,WALK'
        url += '&maxWalkDistance={0}'.format(MAXW)
        url += '&arriveBy=true'
        url += '&optimize=QUICK'
        response = requests.get(url).json()

        responses[cols[0]].append(vals[0])
        if 'plan' in response:
            r = response['plan']['itineraries']

            responses[cols[1]].append(r[0]['duration']/60)
            responses[cols[2]].append(r[0]['walkTime']/60)
            responses[cols[3]].append(r[0]['transitTime']/60)
            responses[cols[4]].append(r[0]['walkDistance']/1609.34)
            responses[cols[5]].append(r[0]['transfers'])
            responses[cols[6]].append('Successful Run')
        else:
            responses[cols[1]].append(None)
            responses[cols[2]].append(None)
            responses[cols[3]].append(None)
            responses[cols[4]].append(None)
            responses[cols[5]].append(None)
            responses[cols[6]].append(response['error']['msg'][0:14])

    lg.info('index ' + str(index) + ' done processing: ' + str(wid))
    return responses
