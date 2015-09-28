import psycopg2
import datetime
import Utils
import random

class Pattern(object):
    def __init__(self):
        self.init_db()
        
        self.sensor_data = {}
        
    def init_db(self):
        print "Connecting to database ......"
        self.conn_to = psycopg2.connect(host='osm-workspace-2.cfmyklmn07yu.us-west-2.rds.amazonaws.com', port='5432', database='osm', user='ds', password='ds2015')
        if self.conn_to:
            print "Connected."
        self.cursor = self.conn_to.cursor()
        
    def close_db(self):
        self.conn_to.commit()
        self.conn_to.close()
        
    def locate_links(self, road_name, function_class_numeric):
    #find (lon, lat) of (from_node, to_node) of all links on the certain highway or arterial
    
        print "Begin locating links on " + road_name
        
        link_loc = {}
    
        if function_class_numeric == 1:
            sql = "select link_id, from_node_id, to_node_id from links where function_class_numeric=1 and name_default like '%" + road_name + "%'"
        else:
            sql = "select link_id, from_node_id, to_node_id from links where function_class_numeric in (3,4) and upper(name_default) like '%" + road_name + "%'"
        self.cursor.execute(sql)
        nodes = self.cursor.fetchall()
        for (link_id, from_node_id, to_node_id) in nodes:
            sql = "select ST_AsText(geom) from nodes where node_id =" + str(from_node_id)
            self.cursor.execute(sql)
            from_node_pos = self.cursor.fetchall()[0][0]
            from_node_loc = Utils.extract_loc_from_geometry(from_node_pos)
            
            sql = "select ST_AsText(geom) from nodes where node_id =" + str(to_node_id)
            self.cursor.execute(sql)
            to_node_pos = self.cursor.fetchall()[0][0]
            to_node_loc = Utils.extract_loc_from_geometry(to_node_pos)
            
            link_loc[link_id] = (from_node_loc, to_node_loc)

        
        return link_loc
    
    def locate_sensors(self, onstreet, direction, function_class_numeric):
    #locate all sensors on the road
        print "Locating Sensors"
        if function_class_numeric == 1:
            sql = "select distinct sensor_id, ST_AsText(start_lat_long) from highway_congestion_config where last_seen_at >= '2015-01-01' and last_seen_at < '2016-01-01' and onstreet like '%" + onstreet + "%' and direction = '" + str(direction) +"'"
        else:
             sql = "select distinct sensor_id, ST_AsText(start_lat_long) from arterial_congestion_config where last_seen_at >= '2015-01-01' and last_seen_at < '2016-01-01' and upper(onstreet) like '%" + onstreet + "%' and direction = '" + str(direction) +"'"
        self.cursor.execute(sql)
        sensors = self.cursor.fetchall()
        sensor_loc = {}
        for s in sensors:
            if s[0] not in sensor_loc:
                sensor_loc[s[0]] = Utils.extract_loc_from_geometry(s[1])
        
        return sensor_loc
    
    def map_link_sensor(self, sectionid):
    #fetch mapping information from database
        print "fetching mapping information from database"
        sql = "select link_id, sensor_id from ss_sensor_mapping where section_id = 'Section " + str(sectionid) + "'"
        self.cursor.execute(sql)
        mapping = self.cursor.fetchall()
        dict_link_sensor = {}
        for m in mapping:
            if m[0] not in dict_link_sensor:
                dict_link_sensor[m[0]] = []
            dict_link_sensor[m[0]].append(m[1])
            if m[1] not in self.sensor_data:
                self.sensor_data[m[1]] = {}
        
        return dict_link_sensor
        
    def realtime_pattern(self, road_name, function_class_numeric, direction, sectionid):
    #get realtime_pattern of section
        link_loc = lapattern.locate_links(road_name, function_class_numeric)
        sensor_loc = lapattern.locate_sensors(road_name, direction, function_class_numeric)
        dict_link_sensor = lapattern.map_link_sensor(sectionid)
        
        start_dt = "2015-09-18 06:00:00"
        end_dt = "2015-09-24 21:00:00"
        for sensor in self.sensor_data:
            print "realtime_data preprocessing of sensor", sensor
            if function_class_numeric == 1:
                sql = "Select timestamp, speed from  sensor_data_highway where sensor_id= "+str(sensor)+" and speed > 1 and speed < 150 and STATUS_Ok=TRUE and timestamp >= '"+start_dt+"' and timestamp <= '"+end_dt+"'"
            else:
                sql = "Select timestamp, speed from  sensor_data_arterial where sensor_id= "+str(sensor)+" and speed > 1 and speed < 150 and STATUS_Ok=TRUE and timestamp >= '"+start_dt+"' and timestamp <= '"+end_dt+"'"
            self.cursor.execute(sql)
            result = self.cursor.fetchall()
            for dt, speed in result:
                dt = dt.replace(second = 0)
                if dt.minute >=0 and dt.minute < 15:
                    dt = dt.replace(minute = 0)
                elif dt.minute >=15 and dt.minute < 30:
                    dt = dt.replace(minute = 15)
                elif dt.minute >=30 and dt.minute < 45:
                    dt = dt.replace(minute = 30)
                elif dt.minute >=45 and dt.minute < 60:
                    dt = dt.replace(minute = 45)
                    
                str_dt = dt.strftime("%Y-%m-%d %H:%M:%S")
                dt = datetime.datetime.strptime(str_dt, "%Y-%m-%d %H:%M:%S")

                if dt not in self.sensor_data[sensor]:
                    self.sensor_data[sensor][dt] = []
                self.sensor_data[sensor][dt].append(speed)
                        
        day_spd = {}
        for d in range(0, 7):
            if d == 0:
                dat = "2015-09-21"
            elif d == 1:
                dat = "2015-09-22"
            elif d == 2:
                dat = "2015-09-23"
            elif d == 3:
                dat = "2015-09-24"
            elif d == 4:
                dat = "2015-09-18"
            elif d == 5:
                dat = "2015-09-19"
            elif d == 6:
                dat = "2015-09-20"
            str_dt = dat + " 6:00:00"
            dt = datetime.datetime.strptime(str_dt, "%Y-%m-%d %H:%M:%S")
            day_spd[d] = []
            for t in range(0, 60):
                dt_end = dt+datetime.timedelta(minutes=15)
                link_spd = {}
                for link in dict_link_sensor:
                    avg_spd = []
                    for sensor in dict_link_sensor[link]: 
                        loc = sensor_loc[sensor]
                        if dt in self.sensor_data[sensor]:
                            s = self.sensor_data[sensor][dt]
                            spd = sum(s)/len(s)
                            avg_spd.append([spd, loc])
                    if len(avg_spd) == 0:
                        print "No available data for link:", link
                    elif len(avg_spd) == 1:
                        link_spd[link] = float(avg_spd[0][0])
                        #print "With sensor on it, average speed on link", link, "from", dt, "to", dt_end, "is", link_spd[link]
                    else:
                        mid_lon = (link_loc[link][0][0] + link_loc[link][1][0]) / 2.0
                        mid_lat = (link_loc[link][0][1] + link_loc[link][1][1]) / 2.0
                        if direction == 0 or direction == 1:
                            dist1 = abs(mid_lat-avg_spd[0][1][1])
                            dist2 = abs(mid_lat-avg_spd[1][1][1])
                        else:
                            dist1 = abs(mid_lon-avg_spd[0][1][0])
                            dist2 = abs(mid_lon-avg_spd[1][1][0])
                        link_spd[link] = (float(avg_spd[0][0])*dist2+float(avg_spd[1][0])*dist1)/(dist1+dist2)
                        #print "Without sensor on it, average speed on link", link, "from", dt, "to", dt_end, "is average of", avg_spd[0][0], "and", avg_spd[1][0], "to be", link_spd[link]
                
                total_len = 0
                weighted_spd = 0
                for link in link_spd:
                    link_len = Utils.map_dist(link_loc[link][0][0], link_loc[link][0][1], link_loc[link][1][0], link_loc[link][1][1])
                    total_len += link_len
                    weighted_spd += link_spd[link] * link_len
                
                if total_len > 0:
                    day_spd[d].append(weighted_spd/total_len)   
                    print "Average speed from", dt, "to", dt_end,"is", day_spd[d][len(day_spd[d])-1]
                else:
                    day_spd[d].append(0)
                    print "Average speed from", dt, "to", dt_end,"is missing"
                
                dt = dt_end
        
        return day_spd
    
    def historic_pattern(self, road_name, function_class_numeric, direction, sectionid):
        link_loc = lapattern.locate_links(road_name, function_class_numeric)
        sensor_loc = lapattern.locate_sensors(road_name, direction, function_class_numeric)
        dict_link_sensor = lapattern.map_link_sensor(sectionid)
        
        print "Connecting to database ......"
        his_conn_to = psycopg2.connect(host='graph-3.cfmyklmn07yu.us-west-2.rds.amazonaws.com', port='5432', database='tallygo', user='ds', password='ds2015')
        if his_conn_to:
            print "Connected."
        his_cursor = his_conn_to.cursor()
        
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        
        print "historical_data preprocessing"
        day_link_weight = {}
        for d in range(0, 7):
            day = days[d]
            day_link_weight[d] = {}
            for link in dict_link_sensor:
                sql = "select from_node_id, to_node_id from links where link_id = " + str(link)
                self.cursor.execute(sql)
                start_node, end_node = self.cursor.fetchall()[0]
                
                sql = "select weights from edge_weight_metric_"+day+" WHERE start_originalid = " + str(start_node) + " AND end_originalid = "+str(end_node)
                his_cursor.execute(sql)
                weights = his_cursor.fetchall()[0][0]
                day_link_weight[d][link] = weights
            
            
        day_spd = {}
        for d in range(0, 7):
            day = days[d]
            day_spd[d] = []
            for w in range(0, 60):
                link_weight = {}
                for link in dict_link_sensor:
                    link_weight[link] = []
                    weight = day_link_weight[d][link][w]
                    if weight:
                        link_weight[link] = weight
                        #print "Weight on link",link,"is",weight
                    else:
                        print "No available weight on link", link
                
                total_len = 0
                total_weight = 0
                for link in link_weight:
                    link_len = Utils.map_dist(link_loc[link][0][0], link_loc[link][0][1], link_loc[link][1][0], link_loc[link][1][1])
                    total_len += link_len
                    total_weight += link_weight[link]
                
                if total_weight >0:
                    spd = (total_len/total_weight) * 3600.0
                    day_spd[d].append(spd)
                    print "Average speed in weight ",w,"on",days[d], "is",spd
                else:
                    day_spd[d].append(0)
                    print "No available weight in weight",w
                
        his_conn_to.close()
        
        return day_spd

                
        
    
if __name__ == '__main__':
    lapattern = Pattern()
    
    #First Highway Section
    sectionid = 1
    road_name = "I-105"
    function_class_numeric = 1 #1: Highway 3:Arterial
    direction = 2    #0:N 1:S 2:E 3:W
    
    rt_pt = lapattern.realtime_pattern(road_name, function_class_numeric, direction, sectionid)
    his_pt = lapattern.historic_pattern(road_name, function_class_numeric, direction, sectionid)
    
    for day in rt_pt:
        days = ["'Monday'", "'Tuesday'", "'Wednesday'", "'Thursday'", "'Friday'", "'Saturday'", "'Sunday'"]
        rt_str = "'{"
        his_str = "'{"
        for i in range(0, 60):
            if rt_pt[day][i] == 0:
                print "!!!!!!!!!!Emergency filling!!!!!!!!!!!!"
                rt_pt[day][i] = his_pt[day][i] * random.uniform(0.9, 1.1)
            if i == 0:
                rt_str += str(rt_pt[day][i]) 
                his_str += str(his_pt[day][i])
            else:
                rt_str += "," + str(rt_pt[day][i])
                his_str += "," + str(his_pt[day][i])
        rt_str += "}'"
        his_str += "}'"
        sql = "insert into SS_SECTION_PATTERN(section_id, day, realtime_pattern, historical_pattern) values(%s,%s,%s,%s)"%("'Section 1'", days[day], rt_str, his_str)
        lapattern.cursor.execute(sql)
        
    lapattern.conn_to.commit()
    
    #Second Highway Section
    sectionid = 2
    road_name = "I-405"
    function_class_numeric = 1 #1: Highway 3:Arterial
    direction = 0    #0:N 1:S 2:E 3:W
    
    rt_pt = lapattern.realtime_pattern(road_name, function_class_numeric, direction, sectionid)
    his_pt = lapattern.historic_pattern(road_name, function_class_numeric, direction, sectionid)
    
    for day in rt_pt:
        days = ["'Monday'", "'Tuesday'", "'Wednesday'", "'Thursday'", "'Friday'", "'Saturday'", "'Sunday'"]
        rt_str = "'{"
        his_str = "'{"
        for i in range(0, 60):
            if rt_pt[day][i] == 0:
                print "!!!!!!!!!!Emergency filling!!!!!!!!!!!!"
                rt_pt[day][i] = his_pt[day][i] * random.uniform(0.9, 1.1)
            if i == 0:
                rt_str += str(rt_pt[day][i]) 
                his_str += str(his_pt[day][i])
            else:
                rt_str += "," + str(rt_pt[day][i])
                his_str += "," + str(his_pt[day][i])
        rt_str += "}'"
        his_str += "}'"
        sql = "insert into SS_SECTION_PATTERN(section_id, day, realtime_pattern, historical_pattern) values(%s,%s,%s,%s)"%("'Section 2'", days[day], rt_str, his_str)
        lapattern.cursor.execute(sql)
        
    lapattern.conn_to.commit()
    
    #Third Highway Section
    sectionid = 3
    road_name = "I-710"
    function_class_numeric = 1
    direction = 0    #0:N 1:S 2:E 3:W
    
    rt_pt = lapattern.realtime_pattern(road_name, function_class_numeric, direction, sectionid)
    his_pt = lapattern.historic_pattern(road_name, function_class_numeric, direction, sectionid)
    
    for day in rt_pt:
        days = ["'Monday'", "'Tuesday'", "'Wednesday'", "'Thursday'", "'Friday'", "'Saturday'", "'Sunday'"]
        rt_str = "'{"
        his_str = "'{"
        for i in range(0, 60):
            if rt_pt[day][i] == 0:
                rt_pt[day][i] = his_pt[day][i] * random.uniform(0.9, 1.1)
            if i == 0:
                rt_str += str(rt_pt[day][i]) 
                his_str += str(his_pt[day][i])
            else:
                rt_str += "," + str(rt_pt[day][i])
                his_str += "," + str(his_pt[day][i])
        rt_str += "}'"
        his_str += "}'"
        sql = "insert into SS_SECTION_PATTERN(section_id, day, realtime_pattern, historical_pattern) values(%s,%s,%s,%s)"%("'Section 3'", days[day], rt_str, his_str)
        lapattern.cursor.execute(sql)
        
    lapattern.conn_to.commit()
                
    #First Arterial Section
    sectionid = 4
    road_name = "NORMANDIE"
    function_class_numeric = 3
    direction = 1    #0:N 1:S 2:E 3:W
    
    rt_pt = lapattern.realtime_pattern(road_name, function_class_numeric, direction, sectionid)
    his_pt = lapattern.historic_pattern(road_name, function_class_numeric, direction, sectionid)
    
    for day in rt_pt:
        days = ["'Monday'", "'Tuesday'", "'Wednesday'", "'Thursday'", "'Friday'", "'Saturday'", "'Sunday'"]
        rt_str = "'{"
        his_str = "'{"
        for i in range(0, 60):
            if rt_pt[day][i] == 0:
                rt_pt[day][i] = his_pt[day][i] * random.uniform(0.9, 1.1)
            if i == 0:
                rt_str += str(rt_pt[day][i]) 
                his_str += str(his_pt[day][i])
            else:
                rt_str += "," + str(rt_pt[day][i])
                his_str += "," + str(his_pt[day][i])
        rt_str += "}'"
        his_str += "}'"
        sql = "insert into SS_SECTION_PATTERN(section_id, day, realtime_pattern, historical_pattern) values(%s,%s,%s,%s)"%("'Section 4'", days[day], rt_str, his_str)
        lapattern.cursor.execute(sql)
        
    lapattern.conn_to.commit()
        
    #Second Arterial Section
    sectionid = 5
    road_name = "BEVERLY"
    function_class_numeric = 3
    direction = 3    #0:N 1:S 2:E 3:W
    
    rt_pt = lapattern.realtime_pattern(road_name, function_class_numeric, direction, sectionid)
    his_pt = lapattern.historic_pattern(road_name, function_class_numeric, direction, sectionid)
    
    for day in rt_pt:
        days = ["'Monday'", "'Tuesday'", "'Wednesday'", "'Thursday'", "'Friday'", "'Saturday'", "'Sunday'"]
        rt_str = "'{"
        his_str = "'{"
        for i in range(0, 60):
            if rt_pt[day][i] == 0:
                rt_pt[day][i] = his_pt[day][i] * random.uniform(0.9, 1.1)
            if i == 0:
                rt_str += str(rt_pt[day][i]) 
                his_str += str(his_pt[day][i])
            else:
                rt_str += "," + str(rt_pt[day][i])
                his_str += "," + str(his_pt[day][i])
        rt_str += "}'"
        his_str += "}'"
        sql = "insert into SS_SECTION_PATTERN(section_id, day, realtime_pattern, historical_pattern) values(%s,%s,%s,%s)"%("'Section 5'", days[day], rt_str, his_str)
        lapattern.cursor.execute(sql)
        
    lapattern.conn_to.commit()
        
    #Third Arterial Section
    sectionid = 6
    road_name = "GRAND"
    function_class_numeric = 3
    direction = 1   #0:N 1:S 2:E 3:W
    
    rt_pt = lapattern.realtime_pattern(road_name, function_class_numeric, direction, sectionid)
    his_pt = lapattern.historic_pattern(road_name, function_class_numeric, direction, sectionid)
    
    for day in rt_pt:
        days = ["'Monday'", "'Tuesday'", "'Wednesday'", "'Thursday'", "'Friday'", "'Saturday'", "'Sunday'"]
        rt_str = "'{"
        his_str = "'{"
        for i in range(0, 60):
            if rt_pt[day][i] == 0:
                rt_pt[day][i] = his_pt[day][i] * random.uniform(0.9, 1.1)
            if i == 0:
                rt_str += str(rt_pt[day][i]) 
                his_str += str(his_pt[day][i])
            else:
                rt_str += "," + str(rt_pt[day][i])
                his_str += "," + str(his_pt[day][i])
        rt_str += "}'"
        his_str += "}'"
        sql = "insert into SS_SECTION_PATTERN(section_id, day, realtime_pattern, historical_pattern) values(%s,%s,%s,%s)"%("'Section 6'", days[day], rt_str, his_str)
        lapattern.cursor.execute(sql)
        
    lapattern.conn_to.commit()
    
    lapattern.closedb()
    
    
    
    
    