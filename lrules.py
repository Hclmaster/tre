import myglobal
from ltinter import *
from ldata import *
from lunify import *
import copy
import operator as op

Symbol = str    # A Lisp Symbol is implemented as a Python str
List   = list   # A Lisp List   is implemented as a Python list

class Rule(object):

    def __init__(self, counter=0, dbclass=None, trigger=None,
                 body=None, environment={}, label=[]):
        self.counter = counter
        self.dbclass = dbclass
        self.trigger = trigger
        self.body = body
        self.environment = environment
        self.label = label

################ Global Environment

def standard_env():
    "An environment with some Lisp standard procedures."
    env = {}
    env.update({
        'mod':op.mod,
        '+':op.add, '-':op.sub, '*':op.mul, '/':op.truediv,
        '>':op.gt, '<':op.lt, '>=':op.ge, '<=':op.le, '=':op.eq,
        'eql':op.eq
    })
    return env

global_env = standard_env()


def showRules():
    """
    Print a list of all rules within the default ltre.
    :return:
    """
    counter = 0
    for key,dbclass in myglobal._ltre_.dbclassTable.items():
        for rule in dbclass.rules:
            counter += 1
            printRule(rule)
    return counter

def tokenize(chars: str) -> list:
    return chars.replace('(', '( ').replace(')', ' )').split()

def parse(program: str):
    return read_from_tokens(tokenize(program))

def read_from_tokens(tokens: list):
    if len(tokens) == 0:
        raise SyntaxError('unexpected EOF')
    token = tokens.pop(0)
    if token == '(':
        L = []
        while tokens[0] != ')':
            L.append(read_from_tokens(tokens))
        tokens.pop(0)
        return L
    elif token == ')':
        raise SyntaxError('unexcepted )')
    else:
        return atom(token)

def atom(token: str):
    try: return int(token)
    except ValueError:
        try: return float(token)
        except ValueError:
            return Symbol(token)

#### eval
def eval(x, env=global_env):
    # all values in the parse result list are symbol!
    if x[0] == Symbol('rule'):
        addRule(x[1], x[2:])
    elif x[0] == Symbol('assert!'):
        assertFact(x[1:][0])
    elif x[0] == Symbol('rassert!'):
        assertFact(x[1:][0])
    elif isinstance(x, Symbol):      # variable reference
        if x in env:
            return env[x]
        else:
            return x
    elif not isinstance(x, List):  # constant literal
        return x
    elif x[0] == 'when':
        (_, test, conseq) = x
        exp = (conseq if eval(test, env) else None)
        return eval(exp, env)
    else:                          # (proc arg...)
        proc = eval(x[0], env)
        args = [eval(exp, env) for exp in x[1:]]
        return proc(*args)

def addRule(trigger, body):
    # First build the struct
    myglobal._ltre_.rule_counter += 1
    rule = Rule(trigger=trigger, body=body,
                counter=myglobal._ltre_.rule_counter, environment=myglobal._env_)

    # Now index it
    dbclass = getDbClass(trigger, myglobal._ltre_)
    dbclass.rules.append(rule)
    rule.dbclass = dbclass
    #print("====== debugging the ltre with New Rule =======")
    #printRule(rule)

    # Go into the database and see what it might trigger on

    print('candidates', getCandidates(trigger, myglobal._ltre_))

    #for candidate in getCandidates(trigger, myglobal._ltre_):
        #tryRuleOn(rule, candidate, myglobal._ltre_)

    constructCandidates(getCandidates(trigger, myglobal._ltre_), rule, 0, len(trigger))


def constructCandidates(candidates, rule, idx, level, ans=[]):
    #print('is it here????')
    if idx == level:
        tryRuleOn(rule, ans, myglobal._ltre_)
        return

    for candidate in candidates[idx]:
        ans.append(candidate)
        constructCandidates(candidates, rule, idx+1, level, ans)
        ans.pop()

def printRule(rule):
    """
    Print representation of rule
    :param rule:
    :return:
    """
    print("Rule #", rule.counter, rule.trigger, rule.body)

def tryRules(fact, ltre):
    #print('tryRules Fact => ', fact)
    for rule in getCandidateRules(fact, ltre):
        #printRule(rule)
        tryRuleOn(rule, fact, ltre)

def getCandidateRules(fact, ltre):
    """
    Return lists of all applicable rules for a given fact
    :param fact:
    :param ltre:
    :return:
    """
    return getDbClass(fact, ltre).rules

def tryRuleOn(rule, fact, ltre):
    """
    Try a single rule on a single fact
    If the trigger matches, queue it up
    :param rule:
    :param fact:
    :param ltre:
    :return:
    """
    #print('tryRuleOn ====== ')
    #print('rule trigger => ', rule.trigger, ' fact => ', fact)
    #print('rule environment => ', rule.environment)
    #print('rule len => ', rule.trigger)
    #print('fact len => ', fact)

    if len(rule.trigger) != len(fact):
        return None
    else:
        bindings = unify(fact, rule.trigger, rule.environment)

    #print('bindings ???? ', bindings)

    if bindings != None:
        enqueue([rule.body, bindings], ltre)

def runRules(ltre):
    counter = 0
    #print('runRules length ===> ', len(ltre.queue))
    while len(ltre.queue) > 0:
        rulePair = dequeue(ltre)
        counter += 1
        runRule(rulePair, ltre)

    if ltre.debugging:
        print('Total', counter, 'rules run!')

# It's a LIFO queue
def enqueue(new, ltre):
    ltre.queue.append(new)

def dequeue(ltre):
    if len(ltre.queue) > 0:
        return ltre.queue.pop()
    else:
        return None

def runRule(pair, ltre):
    """
    Here pair is ([body], {bindings})
    :param pair:
    :param ltre:
    :return:
    """
    myglobal._env_ = pair[1]
    myglobal._ltre_ = ltre

    ltre.rules_run += 1

    #print("======= run Rule Part =========")
    #print('body ===> ', pair[0])
    #print('bindings => ', pair[1])
    newBody = copy.deepcopy(pair[0])

    newBody[0] = bindVar(newBody[0], pair[1])
    #print('newnewnew body => ', newBody[0])
    eval(newBody[0])

def bindVar(lst, bindings):
    for item in lst:
        for key, value in bindings.items():
            if key in item:
                item[item.index(key)] = value
        if any(isinstance(item, list) for i in item):
            item = bindVar(item, bindings)

    return lst

if __name__ == '__main__':
    forms = ['(rule (implies ?ante ?conse) (rule ?ante (assert! ?conse)))',
             '(rule (not (not ?x)) (assert! ?x))']
    """
    for form in forms:
        print('form => ', form)
        print("tokenize result ======>")
        print(tokenize(form))
        print("parse result =====> ")
        print(parse(form))
    """