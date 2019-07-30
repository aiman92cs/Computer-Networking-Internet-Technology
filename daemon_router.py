"""COSC 364 RIP ROUTING
WRITTEN BY:
Aiman Hazashah
Ariel Evangelista

Last Updated: April 20, 2018
"""

#Modules needed
import os
import socket
import select
import sys
import time
import random

# GLOBAL VARIABLES FROM CONFIGURATION FILES
own_id = -1
output_ports = {}
input_ports = []
next_routers = []
nroutes = []

def print_table(table):
    """Prints the routing table in a nice readable format
       Takes a dictionary variable containing all the current routing info"""
    
    os.system('clear') # clears the screen
    routerids = sorted(table.keys())
    print("\n\n\nRouter ID: {0}".format(own_id))
    print("┌────┬┬────────┬────┬─────────┬──────────┬──────────┐")
    print("│ ID ││Next Hop│Cost│ GrbgFlg │ Time Out │  Garbage │")
    print("├────┼┼────────┼────┼─────────┼──────────┼──────────┤")
    for i in range(0, len(table)):
        info = table[routerids[i]]
        print("│ {:>2} ││".format(routerids[i]), end='')
        print(" {:>6} │ {:>2} │ {:<7} │ {:<8.2f} │ {:<8.2f} │"\
              .format(info[0], info[1], info[2], float(str(info[3][0])[:8]), float(str(info[3][1])[:11])))
    print("└────┴┴────────┴────┴─────────┴──────────┴──────────┘")
    print("\n")
        
def next_hop(next_hop, table):
    """Returns the next hops of routers from the routing table"""
    
    routers = []
    for router in sorted(table.keys()):
        if table[router][0] == next_hop:
            routers.append(router)
    return routers

def routing_table(filenm):
    """Reads configuration file and takes useful information about the
       default routings"""
    global own_id

    
    total = []
    table = {}
    
    c1=open(filenm, 'r')
    for i in c1.readlines():
        i=i.split(', ')
        total.append(i)

    own_id = int(total[0][1])


    for i in range(1, len(total[1])):
        input_ports.append(int(total[1][i]))


    for i in range(1,len(total[2])):
        temp = total[2][i]
        temp = temp.split('-')
        router_id = int(temp[-1])
        portno = int(temp[0])
        output_ports[portno] = router_id
        next_hop = router_id
        metric = int(temp[-2])
        flag = False
        timers = [0, 0]
                
        # LAYOUT [Router: [Next Hop, Cost, Flag, Timers]]
        table[router_id] = [next_hop, metric, flag, timers] 
        # Sets the default neighbour routers for later use
        # This is to be used in case a neighbor routers shuts down and has been
        # restarted.
        next_routers.append([router_id, metric])
        nroutes.append(router_id)
        
    return table

def router_list(t):
    """Returns the list of the current routers from the routing table"""
    hashkey=[]
    table = t
    if table != None:
        for y in table.keys():
            hashkey.append(y)
        return hashkey
    else:
        return hashkey

def listenlist():
    """Neighbour routers that we need to watch"""
    l_list=[]
    for i in range(0, len(input_ports)):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('localhost', int(input_ports[i]) ))        
        l_list.append(sock)
    return l_list

        
def id_in_list(rec_id, table):
    """Checks whether the router exists in the routing table"""
    
    key = router_list(table)
    if rec_id in key:
        return True
    else:
        return False

def receiver(rt_table, timeout):
    """Checks the sockets using select (to handle multiple inputs)
       If it has a message in it, it updates the routing table"""

    socket_list = listenlist() 
    table_key = []
    table = rt_table
    a,b,c = select.select(socket_list,[],[], timeout)
    
    if a != []:
        s = a[0]
        s.settimeout(10)
        data,addr = s.recvfrom(1024)
        data = str(data)
        data = data.replace("b","").replace("'","")
        data = data.split(',')
        src = int(data[2])
        #print("Receiving from Router {}".format(src))
        start = 3
        
        while start < len(data):
            rec_id = int(data[start]) 
            router_id = int(data[start])
            
            # Tries to measure the metric of the received message from neighbours
            # This part will create and error if the source router is not in the
            # routing table. To handle this, we use Try and Except
            try:
                metric = min(int(data[start+1]) + table[src][1], 16)
            except:
                # if the source of the message is not in the routing table
                # It must be a neighbour so we search through the default
                # information we have if the message is from our neighbour
                # and then puts it back to the routing table.
                try:
                    for i in range(0, len(next_routers)):
                        if (src == next_routers[i][0]):
                            n_id = next_routers[i][0]
                            n_metric = next_routers[i][1]
                            n_flag = False
                            n_timers = [0, 0]
                            table[n_id] = [n_id, n_metric, n_flag, n_timers]
                            print_table(table)
                            
                except:            
                    # Drops the packet
                    # If there occurs any errors, there must be a corruption
                    # Or was not in a correct format
                    pass
            
            # Checks the length of the packet if there is one
            try:
                if metric not in range(0,17):
                    print("Packet does not conform. Metric not in range 0-16")
            except:
                # Drops the packet
                # If there occurs any errors, there must be a corruption
                # Or was not in a correct format
                pass
    
            # Updates the table based on the message received
            try:
                if router_id not in output_ports.values() and router_id != own_id:
                    if not id_in_list(rec_id, table) and metric < 16:
                        # If the route is not registered to our routing table
                        # and IS reachable, add it to the routing table
                        table[router_id] = [src, metric, False, [0,0]]
                
                    if (metric < table[router_id][1]):
                        # A better route is discovered
                        table[router_id][1] = metric 
                        table[router_id][0] = src
                
                    if (src == table[router_id][0]):
                        # Submitting to the information the router gives us if they
                        # are the first hop to the destination.
                        table[router_id][1] = metric 
                        table[router_id][0] = src
                        table[router_id][-1][0] = 0 # Reset Timer
                        table[src][-1][1] = 0
                        table[router_id][2] = False                        
                    
            except:
                #Drops the packet
                #If there occurs any errors, there must be a corruption
                #Or was not in a correct format
                pass
            
            #Move to the next routing data
            start += 2


        #Resets all timers if under 16, but not the garbage collection if it
        #is over 16 because 16 means infinity
        try:
            table[src][-1][0] = 0 
            table[src][-1][1] = 0                
            table[src][2] = False
        except:
            #Bypass any error in here as we really doesn't care if the router
            #isn't registered in the table so we don't need to worry about timers
            pass
        
    return table

def create_message(t, port, recipient):
    """Creates a 'packet' (comma separated values) with routing information 
       and sends it to the port"""

    #Simulates a packet using string separated by commas
    table = t # {}
    command = "2" # Command No.: 2
    version = "2" # Version No.: 2
    source = own_id
    key = router_list(table)
    head = command + ',' + version + ','+ str(source)
    result = head
    
    for i in key:
        value = table[i]
        #Split Horizon to Prevent Count to Infinity Problem
        if (recipient == value[0]):
            #If sending updates and it happens that the router we are sending
            #it to is also the next hop, it will skip this update and proceed 
            #to next route
            pass
        else:
            result += ',' + str(i) + ','
            metric = str(value[1]) if i not in table.values() else 16
            result += metric
 
    return result

def send_message(table):
    """Sends a message (packet) that contains all routing information about
       this router"""

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for port in output_ports:
        #Table: Routing Table (Dictionary)
        #Port: Ports retrieved from Config Files
        #Output_Ports[port]: The router on which we will send it to
        msg = create_message(table, port, output_ports[port])
        msg = msg.encode('utf-8')
    
        sock.sendto(msg, ("localhost", port))

def update_timers(table, time):
    """Adds time to all timers from the routing table"""
    
    #Default Timers Setup
    route_invalid_timeout = 30
    garbage_collection_timeout = 24

    for key in sorted(table.keys()):
        if table[key][2]:
            table[key][-1][1] += time
            #This timer initiates the removal of a routing entry
            if table[key][-1][1] > garbage_collection_timeout:
                del table[key]
        else:
            table[key][-1][0] += time
            if table[key][-1][0] > route_invalid_timeout:
                #Sets routing cost to 16 and flags it
                table[key][1] = 16
                table[key][2] = True
                #If we use the flagged router as a next hop to other routers
                #flag them also
                for router in next_hop(key, table):
                    table[router][1] = 16

def run():
    #counter = 0
    try:
        rt_table = routing_table(sys.argv[1])
    except:
        print("Invalid File Format")

    while 1:
        #print("loop " + str(counter))
        maxtime = 2 + random.randint(-2,2)
        timeout = maxtime
        track = time.time()
        elapsed = track - time.time()
        timer_incr = 0

        while elapsed < maxtime:
            rt_table = receiver(rt_table, timeout)
            timer_incr = time.time() - track
            track = time.time()
            update_timers(rt_table, timer_incr)
            elapsed += timer_incr
            timeout = max(maxtime - elapsed, 0)

        print_table(rt_table)
        send_message(rt_table)
        #counter += 1


if __name__ == "__main__":
    n_args = (len(sys.argv))
    if n_args == 2: run()
    else: print("Daemon takes exactly one configuration file.") 


