import requests #need the requests library installed
import json
import numpy as np #need the numpy library installed
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Weather:
    clg_ht : int
    clg_ty : str
    vis : float
    wind_dir : int
    wind_vel : int
    valid : bool

@dataclass
class Airport:
    icaoId : str
    dist : float
    weight : float
    hr0_wx : Weather
    hr1_wx : [Weather, Weather, Weather, Weather, Weather, Weather]
    rawMetar : str
    rawTaf : str

#USER SETTINGS
home_airport = "KSEE"
clg = [4000,2000] # ceiling limits [yes,no]
wind = [10,20] # wind limits [yes,no]
vis = [5,2] # vis limits [yes,no]

#Pull Current Time
now = datetime.now()
hr = int(now.strftime("%H"))+8

print("Pulling airport observation and data for " + home_airport + "...")

#Pull Home Airport
metar_url = "https://beta.aviationweather.gov/cgi-bin/data/metar.php?ids="+home_airport+"&format=json"
home_metar_json = requests.get(metar_url, allow_redirects=True)

home_hr0_wx = Weather(0,"",0.0,0,0,False)
if (home_metar_json.json()[0]["cldCvg1"] == "BKN") or (home_metar_json.json()[0]["cldCvg1"] == "OVC"):
    home_hr0_wx.clg_ty = home_metar_json.json()[0]["cldCvg1"]
    home_hr0_wx.clg_ht = int(home_metar_json.json()[0]["cldBas1"])*100
elif (home_metar_json.json()[0]["cldCvg2"] == "BKN") or (home_metar_json.json()[0]["cldCvg2"] == "OVC"):
    home_hr0_wx.clg_ty = home_metar_json.json()[0]["cldCvg2"]
    home_hr0_wx.clg_ht = int(home_metar_json.json()[0]["cldBas2"])*100
elif (home_metar_json.json()[0]["cldCvg3"] == "BKN") or (home_metar_json.json()[0]["cldCvg3"] == "OVC"):
    home_hr0_wx.clg_ty = home_metar_json.json()[0]["cldCvg3"]
    home_hr0_wx.clg_ht = int(home_metar_json.json()[0]["cldBas3"])*100
else:
    home_hr0_wx.clg_ty = "none"
    home_hr0_wx.clg_ht = 18000
if len(home_metar_json.json()[0]["visib"]) == 4:
    home_hr0_wx.vis = float(home_metar_json.json()[0]["visib"][0:1])+float(home_metar_json.json()[0]["visib"][2:3])/100
if len(home_metar_json.json()[0]["visib"]) == 3:
    home_hr0_wx.vis = float(home_metar_json.json()[0]["visib"][0])+float(home_metar_json.json()[0]["visib"][1:2])/100
else:
    home_hr0_wx.vis = float(home_metar_json.json()[0]["visib"])/100
home_hr0_wx.wind_dir = int(home_metar_json.json()[0]["wdir"])
home_hr0_wx.wind_vel = int(home_metar_json.json()[0]["wspd"])
home_hr0_wx.valid = True

##Pull All Airfields Within ~50 miles
home_lat_float = float(home_metar_json.json()[0]['lat'])
home_lon_float = float(home_metar_json.json()[0]['lon'])
ll_corner_lat = str(home_lat_float-0.8333) #0.8333 is the appromixate degrees latitude to cover 50nm
lon_50nm_degrees = 50/(60*np.cos(home_lat_float*np.pi/180)) #Conversion factor... distance of 1 degree long = 60*cos(lat)
ll_corner_lon = str(home_lon_float-lon_50nm_degrees)
ur_corner_lat = str(home_lat_float+0.8333)
ur_corner_lon = str(home_lon_float+lon_50nm_degrees)

#Pull the airport data for the box
home_area_url = "https://beta.aviationweather.gov/cgi-bin/data/metar.php?bbox="+ll_corner_lat+","+ll_corner_lon+","+ur_corner_lat+","+ur_corner_lon+"&format=json"
home_area_metars_json = requests.get(home_area_url, allow_redirects=True)

#List the airports, find the ones with TAFs
airports = []
for item in home_area_metars_json.json():
    airport = item["icaoId"]
    taf_url = "https://beta.aviationweather.gov/cgi-bin/data/taf.php?ids="+airport+"&format=json"
    taf_json = requests.get(taf_url, allow_redirects=True)
    if taf_json.json():
        airports.append(airport)
is_home_airport_in_list = False
for airport in airports:
    if airport == home_airport:
        is_home_airport_in_list = True
#if is_home_airport_in_list == False:
#    airports.append(home_airport)

#Distance from Home Function
#Takes string input ICAO identifier
#Returns nautical miles great circle distance
def homeDist(icaoId):
    earth_rad = 3443.9308855292 #nm, earth's radius
    url = "https://beta.aviationweather.gov/cgi-bin/data/metar.php?ids="+icaoId+"&format=json"
    metar_json = requests.get(url, allow_redirects=True)
    airport_lat = float(metar_json.json()[0]["lat"])
    airport_lon = float(metar_json.json()[0]["lon"])
    dist_nm = earth_rad*np.arccos((np.cos(np.radians(home_lat_float))*np.cos(np.radians(airport_lat))*np.cos(np.radians(home_lon_float-airport_lon)))+(np.sin(np.radians(home_lat_float))*np.sin(np.radians(airport_lat)))) #calculate great circle distance
    return dist_nm

def populateAirport(icaoId):
    metar_url = "https://beta.aviationweather.gov/cgi-bin/data/metar.php?ids="+icaoId+"&format=json"
    metar_json = requests.get(metar_url, allow_redirects=True)
    metar = metar_json.json()[0]
    taf_url = "https://beta.aviationweather.gov/cgi-bin/data/taf.php?ids="+icaoId+"&format=json"
    taf_json = requests.get(taf_url, allow_redirects=True)
    raw_taf = taf_json.json()[0]["fcsts"]
    taf_time = taf_json.json()[0]["issueTime"]
    taf_time = int(taf_time[len(taf_time)-8:len(taf_time)-6])

    #initialize the current weather from the Metar
    hr0_wx = Weather(0,"",0.0,0,0,False)
    if (metar["cldCvg1"] == "BKN") or (metar["cldCvg1"] == "OVC"):
        hr0_wx.clg_ty = metar["cldCvg1"]
        hr0_wx.clg_ht = int(metar["cldBas1"])*100
    elif (metar["cldCvg2"] == "BKN") or (metar["cldCvg2"] == "OVC"):
        hr0_wx.clg_ty = metar["cldCvg2"]
        hr0_wx.clg_ht = int(metar["cldBas2"])*100
    elif (metar["cldCvg3"] == "BKN") or (metar["cldCvg3"] == "OVC"):
        hr0_wx.clg_ty = metar["cldCvg3"]
        hr0_wx.clg_ht = int(metar["cldBas3"])*100
    else:
        hr0_wx.clg_ty = "none"
        hr0_wx.clg_ht = 18000
    if len(metar["visib"]) == 4:
        hr0_wx.vis = float(metar["visib"][0:1])+float(metar["visib"][2:3])/100
    if len(metar["visib"]) == 3:
        hr0_wx.vis = float(metar["visib"][0])+float(metar["visib"][1:2])/100
    else:
        hr0_wx.vis = float(metar["visib"])/100
    hr0_wx.wind_dir = int(metar["wdir"])
    hr0_wx.wind_vel = int(metar["wspd"])
    hr0_wx.valid = True

    #determine the different forecast windows
    forecast_window = []
    for n in range(len(taf_json.json()[0]["fcsts"])):
        timeFrom = int(taf_json.json()[0]["fcsts"][n]["timeFrom"])
        timeTo = int(taf_json.json()[0]["fcsts"][n]["timeTo"])
        forecast_window.append([timeFrom,timeTo])

    #initialize weather for the next six hours from the TAF
    hr1_wx = []
    for n in range(6):   # length of this needs to match the class definition
        hr1_wx.append(Weather(18000,"none",0.0,0,0,False))
    for n in range(len(hr1_wx)):
        #determine difference from taf issue time for n hours ahead of current time
        fcst_hr = hr + n + 1 # fcst_hr is the two digit zulu time hour that we're looking at the forecast for
        taf_hr_diff = fcst_hr - taf_time #taf_hr_diff is the hours ahead of the taf issue. It is minus one because the issue occurs the hour before the forecast.
        compare_time = int(taf_json.json()[0]["validTimeFrom"]) + (taf_hr_diff*3600) #this is the time that I'll test to ensure I'll looking in the right forecast window
        if (compare_time < forecast_window[0][1]):
            if (raw_taf[0]["cldcvg"][0] == "BKN") or (raw_taf[0]["cldcvg"][0] == "OVC"):
                hr1_wx[n].clg_ty = raw_taf[0]["cldcvg"][0]
                hr1_wx[n].clg_ht = int(raw_taf[0]["cldbas"][0])
            elif (len(raw_taf[0]["cldcvg"]) == 2):
                if (raw_taf[0]["cldcvg"][1] == "BKN") or (raw_taf[0]["cldcvg"][1] == "OVC"):
                    hr1_wx[n].clg_ty = raw_taf[0]["cldcvg"][1]
                    hr1_wx[n].clg_ht = int(raw_taf[0]["cldbas"][1])
            elif (len(raw_taf[0]["cldcvg"]) == 3):
                if (raw_taf[0]["cldcvg"][1] == "BKN") or (raw_taf[0]["cldcvg"][1] == "OVC"):
                    hr1_wx[n].clg_ty = raw_taf[0]["cldcvg"][1]
                    hr1_wx[n].clg_ht = int(raw_taf[0]["cldbas"][1])
                elif (raw_taf[0]["cldcvg"][2] == "BKN") or (raw_taf[0]["cldcvg"][2] == "OVC"):
                    hr1_wx[n].clg_ty = raw_taf[0]["cldcvg"][2]
                    hr1_wx[n].clg_ht = int(raw_taf[0]["cldbas"][2])
            if len(metar["visib"]) == 3:
                hr1_wx[n].vis = float(raw_taf[0]["visib"][0])+float(raw_taf[0]["visib"][1:2])/100
            else:
                hr1_wx[n].vis = float(raw_taf[0]["visib"])/100
            hr1_wx[n].wind_dir = int(raw_taf[0]["wdir"])
            hr1_wx[n].wind_vel = int(raw_taf[0]["wspd"])
            hr1_wx[n].valid = True
        elif (compare_time < forecast_window[1][1]):
            if (raw_taf[1]["cldcvg"][0] == "BKN") or (raw_taf[1]["cldcvg"][0] == "OVC"):
                hr1_wx[n].clg_ty = raw_taf[1]["cldcvg"][0]
                hr1_wx[n].clg_ht = int(raw_taf[1]["cldbas"][0])
            elif (len(raw_taf[1]["cldcvg"]) == 2):
                if (raw_taf[1]["cldcvg"][1] == "BKN") or (raw_taf[1]["cldcvg"][1] == "OVC"):
                    hr1_wx[n].clg_ty = raw_taf[1]["cldcvg"][1]
                    hr1_wx[n].clg_ht = int(raw_taf[1]["cldbas"][1])
            elif (len(raw_taf[1]["cldcvg"]) == 3):
                if (raw_taf[1]["cldcvg"][1] == "BKN") or (raw_taf[1]["cldcvg"][1] == "OVC"):
                    hr1_wx[n].clg_ty = raw_taf[1]["cldcvg"][1]
                    hr1_wx[n].clg_ht = int(raw_taf[1]["cldbas"][1])
                elif (raw_taf[1]["cldcvg"][2] == "BKN") or (raw_taf[1]["cldcvg"][2] == "OVC"):
                    hr1_wx[n].clg_ty = raw_taf[1]["cldcvg"][2]
                    hr1_wx[n].clg_ht = int(raw_taf[1]["cldbas"][2])
            if len(metar["visib"]) == 3:
                hr1_wx[n].vis = float(raw_taf[1]["visib"][0])+float(raw_taf[1]["visib"][1:2])/100
            else:
                hr1_wx[n].vis = float(raw_taf[1]["visib"])/100
            hr1_wx[n].wind_dir = int(raw_taf[1]["wdir"])
            hr1_wx[n].wind_vel = int(raw_taf[1]["wspd"])
            hr1_wx[n].valid = True
        elif (compare_time < forecast_window[2][1]):
            if (raw_taf[2]["cldcvg"][0] == "BKN") or (raw_taf[2]["cldcvg"][0] == "OVC"):
                hr1_wx[n].clg_ty = raw_taf[2]["cldcvg"][0]
                hr1_wx[n].clg_ht = int(raw_taf[2]["cldbas"][0])
            elif (len(raw_taf[2]["cldcvg"]) == 2):
                if (raw_taf[2]["cldcvg"][1] == "BKN") or (raw_taf[2]["cldcvg"][1] == "OVC"):
                    hr1_wx[n].clg_ty = raw_taf[2]["cldcvg"][1]
                    hr1_wx[n].clg_ht = int(raw_taf[2]["cldbas"][1])
            elif (len(raw_taf[2]["cldcvg"]) == 3):
                if (raw_taf[2]["cldcvg"][1] == "BKN") or (raw_taf[2]["cldcvg"][1] == "OVC"):
                    hr1_wx[n].clg_ty = raw_taf[2]["cldcvg"][1]
                    hr1_wx[n].clg_ht = int(raw_taf[2]["cldbas"][1])
                elif (raw_taf[2]["cldcvg"][2] == "BKN") or (raw_taf[2]["cldcvg"][2] == "OVC"):
                    hr1_wx[n].clg_ty = raw_taf[2]["cldcvg"][2]
                    hr1_wx[n].clg_ht = int(raw_taf[2]["cldbas"][2])
            if len(metar["visib"]) == 3:
                hr1_wx[n].vis = float(raw_taf[2]["visib"][0])+float(raw_taf[2]["visib"][1:2])/100
            else:
                hr1_wx[n].vis = float(raw_taf[2]["visib"])/100
            hr1_wx[n].wind_dir = int(raw_taf[2]["wdir"])
            hr1_wx[n].wind_vel = int(raw_taf[2]["wspd"])
            hr1_wx[n].valid = True
        elif (compare_time < forecast_window[3][1]):
            if (raw_taf[3]["cldcvg"][0] == "BKN") or (raw_taf[3]["cldcvg"][0] == "OVC"):
                hr1_wx[n].clg_ty = raw_taf[3]["cldcvg"][0]
                hr1_wx[n].clg_ht = int(raw_taf[3]["cldbas"][0])
            elif (len(raw_taf[3]["cldcvg"]) == 2):
                if (raw_taf[3]["cldcvg"][1] == "BKN") or (raw_taf[3]["cldcvg"][1] == "OVC"):
                    hr1_wx[n].clg_ty = raw_taf[3]["cldcvg"][1]
                    hr1_wx[n].clg_ht = int(raw_taf[3]["cldbas"][1])
            elif (len(raw_taf[3]["cldcvg"]) == 3):
                if (raw_taf[3]["cldcvg"][1] == "BKN") or (raw_taf[3]["cldcvg"][1] == "OVC"):
                    hr1_wx[n].clg_ty = raw_taf[3]["cldcvg"][1]
                    hr1_wx[n].clg_ht = int(raw_taf[3]["cldbas"][1])
                elif (raw_taf[3]["cldcvg"][2] == "BKN") or (raw_taf[3]["cldcvg"][2] == "OVC"):
                    hr1_wx[n].clg_ty = raw_taf[3]["cldcvg"][2]
                    hr1_wx[n].clg_ht = int(raw_taf[3]["cldbas"][2])
            if len(metar["visib"]) == 3:
                hr1_wx[n].vis = float(raw_taf[3]["visib"][0])+float(raw_taf[3]["visib"][1:2])/100
            else:
                hr1_wx[n].vis = float(raw_taf[3]["visib"])/100
            hr1_wx[n].wind_dir = int(raw_taf[3]["wdir"])
            hr1_wx[n].wind_vel = int(raw_taf[3]["wspd"])
            hr1_wx[n].valid = True
        #elif (compare_time < forecast_window[4][1]):
        #    if (raw_taf[4]["cldcvg"][0] == "BKN") or (raw_taf[4]["cldcvg"][0] == "OVC"):
        #        hr1_wx[n].clg_ty = raw_taf[4]["cldcvg"][0]
        #        hr1_wx[n].clg_ht = int(raw_taf[4]["cldbas"][0])
        #    elif (len(raw_taf[4]["cldcvg"]) == 2):
        #        if (raw_taf[4]["cldcvg"][1] == "BKN") or (raw_taf[4]["cldcvg"][1] == "OVC"):
        #            hr1_wx[n].clg_ty = raw_taf[4]["cldcvg"][1]
        #            hr1_wx[n].clg_ht = int(raw_taf[4]["cldbas"][1])
        #    elif (len(raw_taf[4]["cldcvg"]) == 3):
        #        if (raw_taf[4]["cldcvg"][1] == "BKN") or (raw_taf[4]["cldcvg"][1] == "OVC"):
        #            hr1_wx[n].clg_ty = raw_taf[4]["cldcvg"][1]
        #            hr1_wx[n].clg_ht = int(raw_taf[4]["cldbas"][1])
        #        elif (raw_taf[4]["cldcvg"][2] == "BKN") or (raw_taf[4]["cldcvg"][2] == "OVC"):
        #            hr1_wx[n].clg_ty = raw_taf[4]["cldcvg"][2]
        #            hr1_wx[n].clg_ht = int(raw_taf[4]["cldbas"][2])
        #    if len(metar["visib"]) == 3:
        #        hr1_wx[n].vis = float(raw_taf[4]["visib"][0])+float(raw_taf[4]["visib"][1:2])/100
        #    else:
        #        hr1_wx[n].vis = float(raw_taf[4]["visib"])/100
        #    hr1_wx[n].wind_dir = int(raw_taf[4]["wdir"])
        #    hr1_wx[n].wind_vel = int(raw_taf[4]["wspd"])
        #    hr1_wx[n].valid = True
    return Airport(icaoId,homeDist(icaoId),100-homeDist(icaoId),hr0_wx,hr1_wx,metar["rawOb"],taf_json.json()[0]["rawTAF"])

#take all the relevant airports and populate the classes
print("Gathering METARs and TAFs for nearby aerodromes...")
for i in range(len(airports)):
    print("Pulling data for " + airports[i] + "...\n" + str(i+1) + " of " + str(len(airports)) + " aerodromes within range.")
    airports[i] = populateAirport(airports[i])

print("Computing weather decision...")

votes0=[0,0,0] #votes to launch now [yes,maybe,no]
votes1=[votes0,votes0,votes0,votes0,votes0,votes0] #votes to launch at a future time 1-6 hours from now [yes,maybe,no]

#cast votes for the "launch now" decision

#home airport gets 100 votes
if (home_hr0_wx.clg_ht < clg[1]) or (home_hr0_wx.wind_vel >= wind[1]) or (home_hr0_wx.vis < vis[1]):
    votes0[2]+=100
elif (home_hr0_wx.clg_ht >= clg[0]) and (home_hr0_wx.wind_vel < wind[0]) and (home_hr0_wx.vis >= vis[0]):
    votes0[0]+=100
else:
    votes0[1]+=100

#each other airport gets to cast votes relative to their distance to the home airport
for airport in airports:
    if (airport.hr0_wx.clg_ht < clg[1]) or (airport.hr0_wx.wind_vel >= wind[1]) or (airport.hr0_wx.vis < vis[1]):
        votes0[2]+=airport.weight
    elif (airport.hr0_wx.clg_ht >= clg[0]) and (airport.hr0_wx.wind_vel < wind[0]) and (airport.hr0_wx.vis >= vis[0]):
        votes0[0]+=airport.weight
    else:
        votes0[1]+=airport.weight

if max(votes0) == votes0[0]:
    decision0 = "YES"
elif max(votes0) == votes0[1]:
    decision0 = "MAYBE"
else:
    decision0 = "NO"
confidence0 = str(100*max(votes0)/sum(votes0))
confidence0 = confidence0[0:4] + "%"
print("Should I launch now? " + decision0 + " (" + confidence0 + " confidence)")

#cast votes for launch in 1-6 hours decision
decision1=[]
confidence1=[]
for hr in range(6):
    for airport in airports:
        if (airport.hr1_wx[hr].clg_ht < clg[1]) or (airport.hr1_wx[hr].wind_vel >= wind[1]) or (airport.hr1_wx[hr].vis < vis[1]):
            votes1[hr][2]+=airport.weight
        elif (airport.hr1_wx[hr].clg_ht >= clg[0]) and (airport.hr1_wx[hr].wind_vel < wind[0]) and (airport.hr1_wx[hr].vis >= vis[0]):
            votes1[hr][0]+=airport.weight
        else:
            votes1[hr][1]+=airport.weight
    if max(votes1[hr]) == votes1[hr][0]:
        decision1.append("YES")
    elif max(votes1[hr]) == votes1[hr][1]:
        decision1.append("MAYBE")
    else:
        decision1.append("NO")
    confidence1.append(str(100*max(votes0)/sum(votes0)))
    confidence1[hr] = confidence1[hr][0:4] + "%"
    print("Can I launch in " + str(hr+1) + " hour(s)? " + decision1[hr] + " (" + confidence1[hr] + " confidence)")

# Write results to an HTML!
print("Writing results to HTML...")
Func = open("body.html","w")
  
# Adding input data to the HTML file
body = "<html>\n<head>\n<title> \nLooking Up!\n \
           </title>\n</head> <body> <h1> \
           <p><b>Should I fly?</b></p></h1> \
           <h2><p><i>A forecast for the common man.</i></p></h2><p><i>"+home_airport+" ~  \
           Last computed "+now.strftime("%m/%d/%Y, %H:%M:%S")+" Pacific Time</i></p> \
           <table width=\"100%\"><tr><th>Time</th><th>Now</th><th>+1hr</th><th>+2hr</th><th>+3hr</th><th>+4hr</th><th>+5hr</th><th>+6hr</th></tr> \
           <tr><td>Launch?</td><td>"+decision0+"</td><td>"+decision1[0]+"</td><td>"+decision1[1]+"</td><td>"+decision1[2]+"</td> \
           <td>"+decision1[3]+"</td><td>"+decision1[4]+"</td><td>"+decision1[5]+"</td> \
           <tr><td>Confidence</td><td>"+confidence0+"</td><td>"+confidence1[0]+"</td><td>"+confidence1[1]+"</td><td>"+confidence1[2]+"</td> \
           <td>"+confidence1[3]+"</td><td>"+confidence1[4]+"</td><td>"+confidence1[5]+"</td></tr></table><p></p> \
           <table><tr><th>Airport</th><th>METAR</th><th>TAF</th>"
if not is_home_airport_in_list:
    body += "<tr><td>"+home_airport+"</td><td>"+home_metar_json.json()[0]["rawOb"]+"</td><td><i>No TAF</i></td></tr>"
for airport in airports:
    body += "<tr><td>"+airport.icaoId+"</td><td>"+airport.rawMetar+"</td><td>"+airport.rawTaf+"</td></tr>"
body += "</h2></body></html>"
Func.write(body)
# Saving the data into the HTML file
print("Complete!")
Func.close()