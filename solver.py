# mode = "z3"
# mode = "mip"
mode = "gurobi"

eps = 1e-6

class Wrapper:
    def __init__(self, obj):
        self.obj = obj
        self.overwritten = {}
        # delayed to avoid infinite recursion in self.obj = obj
        self.__setattr__ = self.__setattr__2
        
    def __setattr__2(self, name, value):
        self.overwritten[name] = value
        
    # forward all non overwritten attributes to the object
    def __getattr__(self, name):
        if name in self.overwritten:
            return self.overwritten[name]
        return getattr(self.obj, name)

if mode == "mip":
    # compatibility layer for mip to z3
    from mip import *
    s = Model(sense=MINIMIZE, solver_name=CBC)
    
    def Real(name):
        return s.add_var(name=name, var_type=CONTINUOUS)
    
    def Int(name):
        return s.add_var(name=name, var_type=INTEGER)

    def add_constraint(expr):
        global s
        s += expr
        
    def minimize_objective(obj):
        global s
        s.objective = minimize(obj)

    s.add = add_constraint
    s.minimize = minimize_objective
    s.check = lambda: s.optimize()
    sat = OptimizationStatus.OPTIMAL
    
    class Model:
        def __init__(self, s):
            pass
        
        def evaluate(self, expr):
            if isinstance(expr, int):
                return expr
            value = expr.x
            return value
        
        # make subscripting work
        def __getitem__(self, key):
            return self.evaluate(key)
        
    s.model = lambda: Model(s)
        
elif mode == "z3":
    from z3 import *
    s = Optimize()
    
elif mode == "gurobi":
    
    from gurobipy import Model, GRB, quicksum, Var
    
    s = Model()
    s = Wrapper(s)

    used_names = set()        
    
    def Real(name):
        assert name not in used_names
        used_names.add(name)
        return s.addVar(lb=0, name=name)
    
    def Int(name):
        return s.addVar(vtype=GRB.INTEGER, lb=0, name=name)
    
    def add_constraint(expr):
        global s
        s.addConstr(expr)
        
    def minimize_objective(obj):
        global s
        s.setObjective(obj, GRB.MINIMIZE)
        
    def check():
        global s
        s.optimize()
        print("Status:", s.status)
        return s.status

    s.add = add_constraint
    s.minimize = minimize_objective
    s.check = check
    sat = [2,9] # 2 = optimal, 9 = suboptimal
    
    class Model:
        def __init__(self, s):
            pass
        
        def access(self, e, f):
            if isinstance(e, int):
                return e
            value = f(e)
            return value
        
        
        def evaluate(self, expr):
            if isinstance(expr, Var):
                return self.__getitem__(expr)
            return self.access(expr, lambda x: x.getValue())
        
        # make subscripting work
        def __getitem__(self, key):
            return self.access(key, lambda x: x.X)
        
    s.model = lambda: Model(s)
    
    s.Params.TimeLimit = 10 # in seconds
    
else:
    raise ValueError(f"Unknown mode {mode}")

