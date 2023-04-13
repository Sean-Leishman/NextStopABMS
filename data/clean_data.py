from importlib.metadata import requires
import pandas as pd 
import numpy as np
import math
import re
from sklearn.preprocessing import StandardScaler, MinMaxScaler

def fix_string(line):
    if len(line) == 3:
        if line[2] == "C":
            return line[:2] + "00"
        return line[:2] + "0" + line[2:]
    else:
        return line



def process_stations_file(filename, savedfilename, special=None):
    def nextId(row):
        a = df.loc[(df.LINE == row.LINE) & (df.NUMBER > row.NUMBER)]['NUMBER'].min()
        return a

    def prevId(row):
        a = df.loc[(df.LINE == row.LINE) & (df.NUMBER < row.NUMBER)]['NUMBER'].max()
        return a

    df = pd.read_csv(filename)

    df['STN_NO'] = df['STN_NO'].apply(lambda x: fix_string(x))
    df['LINE'] = df['STN_NO'].str[:2]
    df['NUMBER'] = df['STN_NO'].str[2:]
    df = df.fillna(-1)

    df['SUN_INC_START_TIME'] = df['SUN_INC_START_TIME'].astype('int') * 2
    df['INC_END_TIME'] = df['INC_END_TIME'].astype('int') * 2
    df['WEEKDAY_SAT_DEC_START_TIME'] = df['WEEKDAY_SAT_DEC_START_TIME'].astype('int') * 2
    df['WEEKDAY_SAT_INC_START_TIME'] = df['WEEKDAY_SAT_INC_START_TIME'].astype('int') * 2
    df['SUN_DEC_START_TIME'] = df['SUN_DEC_START_TIME'].astype('int') * 2
    df['DEC_END_TIME'] = df['DEC_END_TIME'].astype('int') * 2

    df = df.drop(df.loc[(df.STN_NO == "CC18")].index)

    df['NEXT_STATION_NUMBER'] = df.apply(lambda x: nextId(x) , axis=1)
    df['PREV_STATION_NUMBER'] = df.apply(lambda x: prevId(x) , axis=1)
    
    df.to_csv(savedfilename)

def process_prob_file(filename, savedfilename1, savedfilename2, special=None):
    df1 = pd.read_csv(filename)
    reg = r"(/B.*|^B.*/|/S.*|^S.*/|/P.*|^P.*/)"

    df1['ORIGIN_PT_CODE'] = df1.ORIGIN_PT_CODE.str.replace(reg, "")
    df1['DESTINATION_PT_CODE'] = df1.DESTINATION_PT_CODE.str.replace(reg, "")

    df1 = df1.drop(df1.loc[(df1.ORIGIN_PT_CODE.str.startswith("B")) | (df1.ORIGIN_PT_CODE.str.startswith("P"))| (df1.ORIGIN_PT_CODE.str.startswith("S")) |(df1.DESTINATION_PT_CODE.str.startswith("B")) | (df1.DESTINATION_PT_CODE.str.startswith("P"))| (df1.DESTINATION_PT_CODE.str.startswith("S"))].index)
    
    if special == "TE":
        d = pd.read_csv("new_TE_stations.csv")
        df1 = df1.append(d)

    df1['ORIGIN_PT_CODE'] = df1['ORIGIN_PT_CODE'].str.replace(r"CC4/DT15$","CC4/DT15/CE0")
    df1['DESTINATION_PT_CODE'] = df1['DESTINATION_PT_CODE'].str.replace(r"CC4/DT15$","CC4/DT15/CE0")

    save_shortest_paths(df1, savedfilename2)

    df1 = df1.sort_values(by=['TIME_PER_HOUR','DESTINATION_PT_CODE'])

    total_trips = df1.groupby(["ORIGIN_PT_CODE", "TIME_PER_HOUR", "DAY_TYPE"]).sum().reset_index().rename({"TOTAL_TRIPS":"TOTAL_TRIPS_AGG"},axis=1)
    df1 = pd.merge(df1, total_trips, on=["ORIGIN_PT_CODE","TIME_PER_HOUR", "DAY_TYPE"])

    df1['PROB_TRIP'] = df1.apply(lambda x: round(x['TOTAL_TRIPS']/x['TOTAL_TRIPS_AGG'],3),axis=1)
    df1['CUMSUM'] = df1.groupby(['ORIGIN_PT_CODE','TIME_PER_HOUR','DAY_TYPE'])['PROB_TRIP'].cumsum()

    df1 = df1.drop(['YEAR_MONTH','PT_TYPE','PROB_TRIP','TOTAL_TRIPS_AGG','TOTAL_TRIPS'], axis=1)
    df1 = df1[["DAY_TYPE","TIME_PER_HOUR","ORIGIN_PT_CODE","DESTINATION_PT_CODE","CUMSUM"]]
    df1.to_csv(savedfilename1)

def save_passenger_volume(filename1="weekday_passenger_vol.csv", filename2="weekday_passenger_vol.csv", savedFilename = "passenger_vol.csv", special=None):
    reg = r"(/B.*|^B.*/|/S.*|^S.*/|/P.*|^P.*/)"
    df3 = pd.read_csv("weekday_passenger_vol.csv").rename(columns={"PT_CODE":"ORIGIN_PT_CODE"})
    df4 = pd.read_csv("weekends_passenger_vol.csv").rename(columns={"PT_CODE":"ORIGIN_PT_CODE"})
    df3 = df3.append(df4)
    df3['ORIGIN_PT_CODE'] = df3.ORIGIN_PT_CODE.str.replace(reg, "")
    df3 = df3.drop(df3.loc[(df3.ORIGIN_PT_CODE.str.startswith("B")) | (df3.ORIGIN_PT_CODE.str.startswith("P"))| (df3.ORIGIN_PT_CODE.str.startswith("S"))].index)
    df3['ORIGIN_PT_CODE'] = df3['ORIGIN_PT_CODE'].str.replace(r"CC4/DT15$","CC4/DT15/CE0")
    
    df3.to_csv(savedFilename)

def save_shortest_paths(df1, savedFilename="journey_times.csv"):
    reg = r"(/B.*|^B.*/|/S.*|^S.*/|/P.*|^P.*/)"

    def requiresChange(a,b,c):
        for i in a.split("/"):
             if i[:2] in [x[:2] for x in b.split("/")]:
                 if i[:2] in [x[:2] for x in c.split("/")]:
                     return False 
        
    def isNextId(row1, row2):
        row1s = row1.split("/")
        row2s = row2.split("/")
        for x in row1s:
            for y in row2s:
                if x[:2] == y[:2]:
                    number = int(x[2:]) + 1
                    steps = 1
                    while steps < 3:
                        if int(y[2:]) == number:
                            return True 
                        
                        elif len(cost_df.columns[cost_df.columns.str.contains(x[:2] + f"{number:1}")]) >= 1:
                            return False
                        number += 1
                        steps += 1
            
        return False

    def isPrevId(row1, row2):
        row1s = row1.split("/")
        row2s = row2.split("/")

        for x in row1s:
            for y in row2s:
                if x[:2] == y[:2]:
                    number = int(x[2:]) - 1 
                    steps = -1
                    while number > 0 and steps < 3:
                        if int(y[2:]) == number:
                            return True 
                        elif len(cost_df.columns[cost_df.columns.str.contains(x[:2] + f"{number:1}")]) >= 1:
                            return False
                        number -= 1
                        steps -= 1
            
        return False

    df1['ORIGIN_PT_CODE'] = df1.ORIGIN_PT_CODE.str.replace(reg, "")
    df1['DESTINATION_PT_CODE'] = df1.DESTINATION_PT_CODE.str.replace(reg, "")

    df1 = df1.drop(df1.loc[(df1.ORIGIN_PT_CODE.str.startswith("B")) | (df1.ORIGIN_PT_CODE.str.startswith("P"))| (df1.ORIGIN_PT_CODE.str.startswith("S"))].index)
    df1 = df1.drop(df1.loc[(df1.DESTINATION_PT_CODE.str.startswith("B")) | (df1.DESTINATION_PT_CODE.str.startswith("P"))| (df1.DESTINATION_PT_CODE.str.startswith("S"))].index)
    df1['ORIGIN_PT_CODE'] = df1['ORIGIN_PT_CODE'].str.replace(r"CC4/DT15$","CC4/DT15/CE0")
    df1['DESTINATION_PT_CODE'] = df1['DESTINATION_PT_CODE'].str.replace(r"CC4/DT15$","CC4/DT15/CE0")

    cost_df = df1.groupby(['ORIGIN_PT_CODE','DESTINATION_PT_CODE']).mean().reset_index()
    cost_df = cost_df.pivot(index="ORIGIN_PT_CODE", columns="DESTINATION_PT_CODE", values="TOTAL_TRIPS")

    length = len(df1['ORIGIN_PT_CODE'].unique())
    stations = df1['ORIGIN_PT_CODE'].unique()

    line_dict = {
        'NS': 0,
        'EW': 1,
        'DT': 2,
        'NE': 3,
        'CC': 4,
        'TE': 5,
        'CG': 6,
        'CE': 7,
    }

    cost = [[math.inf] * length for k in range(length)]
    pi = [[0] * length for k in range(length)]
    connections = [[math.inf] * length for k in range(length)]
    lines = [[[]] * length for i in range(length)]

    for i in range(length):
        for j in range(length):
            if i == j:
                cost[i][j] = 0
                connections[i][j] = 0
            elif isNextId(cost_df.index[i],cost_df.columns[j]):
                cost[i][j] = 1
                pi[i][j] = i
                connections[i][j] = 0
            elif isPrevId(cost_df.index[i], cost_df.columns[j]):
                cost[i][j] = 1
                pi[i][j] = i
                connections[i][j] = 0
            for x in [line_dict[y[:2]] for y in cost_df.index[i].split("/")]:
                if x in [line_dict[y[:2]] for y in cost_df.index[j].split("/")]:
                    lines[i][j] = [x]

    for k in range(length):
        for i in range(length):
            for j in range(length):
                if cost[i][k] + cost[k][j] < cost[i][j]:
                    temp = lines[i][k][:]
                    added_cost = 0
                    if temp[-1] != lines[k][j][0]:
                        temp.extend(lines[k][j])
                        added_cost = len(lines[k][j])
                    elif len(lines[k][j]) > 1:
                        temp.extend(lines[k][j][1:])
                        added_cost = 0

                    cost[i][j] = cost[i][k] + cost[k][j] + added_cost
                    pi[i][j] = pi[k][j]

                    lines[i][j] = temp

    pi_df = pd.DataFrame(pi, index=cost_df.index, columns=cost_df.columns)
    pi_df.to_csv(savedFilename)

if __name__ == "__main__":
    #process_stations_file("stations.csv","formatted_stations.csv")
    process_prob_file("origin_destination_train_202302.csv","prob_trip.csv","journey_times.csv", special=None)
    save_passenger_volume(special=None)

    #process_stations_file("stationsTE4.csv","formatted_stationsTE4.csv")
    #process_prob_file("origin_destination_train_202302.csv","prob_tripTE4.csv","journey_timesTE4.csv", special="TE")
    #save_passenger_volume(savedFilename="passenger_volTE4.csv", special="TE")