"""
COSC364 Flow Planning
WRITTEN BY:
Aiman Hazashah
Ariel Evangelista - aev35
"""

# ==============================
# IMPORTS
import os
import time
# GLOBAL VARIABLE(s)
filename = 'flow.lp'    # file to be created
cplex_path = "cplex" # cplex path
# ==============================

def get_input():
    """Gets the number of Nodes"""
    s = int(input("Source Nodes:      "))
    t = int(input("Transit Nodes:     "))
    d = int(input("Destination Nodes: "))
    return s,t,d


def create_nodes(s, t, d):
    """Creates nodes on a list"""
    start = []
    trans = []
    dest = []
    
    for i in range (1, s + 1):
        start.append(str("S" + str(i)))
        
    for i in range (1, t + 1):
        trans.append(str("T" + str(i)))
        
    for i in range (1, d + 1):
        dest.append(str("D" + str(i)))
        
    return start, trans, dest


def get_dem_vol(start, trans, dest):
    """Calculates the demand volume using Hij = i + j"""
    demands = []
    x_var = []
    for s in start:
        for d in dest:
            dem = start.index(s) + dest.index(d) + 2 # 2 for incrementing index
            form = ''
            for t in trans:
                dem_var = "x{}{}{}".format(s, t, d)
                form += dem_var
                x_var.append(dem_var)
                if t != trans[-1]:
                    form += " + "
                else:
                    form += " = {}".format(dem)
            demands.append(form)
    return sorted(demands), sorted(x_var)


def get_source_trans(start, trans, dest):
    """Calculates the link capacity from Source to Transit Nodes with
    some variable ySiTj to make the equation linear"""
    cap = []
    for s in start:
        for t in trans:
            form = ''
            for d in dest:
                form += "x{}{}{}".format(s, t, d)
                if d != dest[-1]:
                    form += " + "
                else:
                    form += " - y{}{} = 0".format(s, t)
            cap.append(form)
    return sorted(cap)


def get_trans_dest(start, trans, dest):
    """Calculates the link capacity from Transit to Destination Nodes with
    some variable yTiDj to make the equation linear"""
    cap = []
    for t in trans:
        for d in dest:
            form = ''
            for s in start:
                form += "x{}{}{}".format(s, t, d)
                if s != start[-1]:
                    form += " + "
                else:
                    form += " - y{}{} = 0".format(t, d)
            cap.append(form)
    return sorted(cap)


def get_source_const(source_trans):
    """Generate constraint for source nodes"""
    constraints = []
    minimum = []
    
    for i in source_trans:
        value = i.split(' ')
        form = "{} - c{} <= 0".format(value[-3], value[-3][1:])
        mini = "{} >= 0".format(value[-3])
        constraints.append(form)
        minimum.append(mini)
        
    return constraints, minimum


def get_trans_const(trans_dest):
    """Generate constraint for destination nodes"""
    constraints = []
    minimum = []
    
    for i in trans_dest:
        value = i.split(' ')
        form = "{} - d{} <= 0".format(value[-3], value[-3][1:])
        mini = "{} >= 0".format(value[-3])
        constraints.append(form)
        minimum.append(mini)
        
    return constraints, minimum
    
    
def get_constraints(source_trans, trans_dest, x_var, start, trans):
    """Generates constraints"""
    constraints = []
    minimum = []
    
    source_const = get_source_const(source_trans)
    constraints += source_const[0]
    minimum += source_const[1]

    trans_const = get_trans_const(trans_dest)
    constraints += trans_const[0]
    minimum += trans_const[1]

    # Generates constraint for all Xijk
    for i in x_var:
        form = "{} >= 0".format(i)
        minimum.append(form)
    
    # Generate r values
    for t in trans:
        form = ''
        for s in start:
            form += "y{}{}".format(s, t)
            if s != start[-1]:
                form += " + "
            else:
                form += " - r <= 0".format(s, t)
        constraints.append(form)    
    
    return [constraints, minimum]


def get_binary_path(start, trans, dest):
    """Generates binary path (Default: 3 | Start -> Transit -> Destination)"""
    paths = []
    binaries = []
    
    # all binary paths when summed, is equal to 3 (S -> T -> D)
    for s in start:
        for d in dest:
            form = ''
            for t in trans:
                var = 'u{}{}{}'.format(s, t, d)
                binaries.append(var)
                if t != trans[-1]:
                    form += '{} + '.format(var)
                else:
                    form += '{} = 3'.format(var)
            paths.append(form)
    
    # paths for demand volumes
    for s in start:
        for t in trans:
            for d in dest:
                dem = start.index(s) + dest.index(d) + 2 # for incrementing index
                dem_var = "{}{}{}".format(s, t, d)
                form = '3 x{} - {} u{} = 0'.format(dem_var, dem, dem_var)
                paths.append(form)
    
    return paths, binaries
    
    
def get_trans_load(trans, x_var):
    """Calculates the demand for each transit nodes"""
    trans_load = []
    
    for t in trans:
        form = 'x'
        for var in x_var:
            if t in var:
                form += var
                form += ' + '
        form = form[1:-3]
        form += ' - l{} = 0'.format(t)
        trans_load.append(form)
    
    return trans_load
    
    
def create_lp(demand_volume, source_trans, trans_dest, constraints, minimum,
              binary_path, binaries, trans_load):
    """Generates an LP file based on the generated optimization problem"""
    form = "Minimize\nr\nSubject to\n"
    
    for i in range(0, len(demand_volume)):
        form += '  {}\n'.format(demand_volume[i])
    
    for i in range(0, len(source_trans)):
        form += '  {}\n'.format(source_trans[i])
        
    for i in range(0, len(trans_dest)):
        form += '  {}\n'.format(trans_dest[i])
        
    for i in range(0, len(constraints)):
        form += '  {}\n'.format(constraints[i])
        
    for i in range(0, len(binary_path)):
        form += '  {}\n'.format(binary_path[i])
        
    for i in range(0, len(trans_load)):
        form += '  {}\n'.format(trans_load[i])
        
    form += 'Bounds\n'
    
    for i in range(0, len(minimum)):
        form += '  {}\n'.format(minimum[i])
    
    form += '  r >= 0\n'
    form += 'Binary\n'
    
    for i in range(0, len(binaries)):
        form += '  {}\n'.format(binaries[i])
        
    form += 'End'

    f = open(filename, 'w')
    f.write(form)
    f.close()
    
    
def run_cplex():
    """Executes cplex via python"""
    
    # CPLEX FULL PATH OF CURRENT MACHINE
    # THIS IS DECLARED ON THE GLOBAL VARIABLES
    #cplex_path = "/home/chaosbib/cplex/cplex/bin/x86-64_linux/cplex"
    #cplex_path = 'cplex'
    
    cplex = cplex_path + " -c 'read {}'".format(filename)
    cplex += " 'optimize' 'display solution variables -'"
    
    os.system(cplex)

    
def main():
    s, t, d = get_input()
    start, trans, dest = create_nodes(s, t, d)
    demand_volume, x_var = get_dem_vol(start, trans, dest)
    source_trans = get_source_trans(start, trans, dest)
    trans_dest = get_trans_dest(start, trans, dest)
    constraints, minimum = get_constraints(source_trans, trans_dest, 
                                           x_var, start, trans)
    binary_path, binaries = get_binary_path(start, trans, dest)
    trans_load = get_trans_load(trans, x_var)
    create_lp(demand_volume, source_trans, trans_dest, constraints, minimum,
              binary_path, binaries, trans_load)
    
    start_time = time.time()
    run_cplex()
    print("\nCPLEX Execution Time: {}".format(time.time() - start_time))
    
    
main()