'''
Created on Jul 2, 2013

@author: felix
'''




class WorldState(object):
    """Storage for values of conditions."""

    def __init__(self, worldstate=None):
        self._condition_values = {}
        if worldstate is not None:
            self._condition_values.update(worldstate._condition_values)

    def __str__(self):
        return '%s {%s}' % (self.__class__.__name__,
                            ', '.join(['%s: %s' % (c, v) for (c, v)
                                       in self._condition_values.iteritems()]
                                      # anti-multiline workaround for message types:
                                      ).replace('\n  ', ' ').replace(' \n', ' ').replace('\n', ' ')
                            )

    def __repr__(self):
        return '<WorldState %X values=%s>' % (id(self), self._condition_values)
#        return '<WorldState>'

    def get_condition_value(self, condition):
        return self._condition_values[condition]

    def set_condition_value(self, condition, value):
        self._condition_values[condition] = value

    def matches(self, start_worldstate):
        """Return whether self is an 'equal subset' of start_worldstate."""
        start_ws_dict = start_worldstate._condition_values
        matches = True
        for (cond, value) in self._condition_values.viewitems():
            if cond in start_ws_dict:
                if not start_ws_dict[cond] == value:
                    matches = False
                    break
        print 'comparing worldstates: ', matches
#        print 'mine:  ', self._condition_values
#        print 'start: ', start_ws_dict
        return matches

    def get_state_name_dict(self):
        """Returns a dictionary with not the conditions themselves but their state_names as keys."""
        return {cond._state_name: val for cond, val in self._condition_values.viewitems()}

    def get_unsatisfied_conditions(self, worldstate):
        """Return a set of conditions that are in both the given and this
        worldstate but have unequal values. By now this is symmetric."""
        common_conditions_set = (self._condition_values.viewkeys() &
                                 worldstate._condition_values.viewkeys())
        unsatisfied_conditions = {condition
                                  for condition in common_conditions_set
                                  if (self.get_condition_value(condition) !=
                                      worldstate.get_condition_value(condition))
                                  }

#        print 'states different: ', ', '.join([str(c) for c in unsatisfied_conditions])
        for condition in unsatisfied_conditions:
            print 'state different: ', condition

        return unsatisfied_conditions


## known as state
class Condition(object):
    """The object that makes any kind of robot or system state available.

    This class, at least its static part, is a multiton:
    * For each state_name only one instance is allowed to be in the
      _conditions_dict mapping.
    * If there is no mapping for a get(state_name) call an assertion is
      triggered, as creating a new instance makes no sense here.

    self._state_name: id name of condition, must not be changed
    """

    def __init__(self, state_name):
        self._state_name = state_name

    def __str__(self):
        return '%s:%s' % (self.__class__.__name__, self._state_name)

    def __repr__(self):
        return '<%s state_name=%s>' % (self.__class__.__name__, self._state_name)

    def get_value(self):
        """Returns the current value, hopefully not blocking."""
        raise NotImplementedError

    def update_value(self, worldstate):
        """Update the condition's current value to the given worldstate."""
        worldstate.set_condition_value(self, self.get_value())



    _conditions_dict = {}

    @classmethod
    def add(cls, condition):
        assert condition._state_name not in cls._conditions_dict, \
            "Condition '" + condition._state_name + "' had already been added previously!"
        cls._conditions_dict[condition._state_name] = condition

    @classmethod
    def get(cls, state_name):
        assert state_name in cls._conditions_dict, "Condition '" + state_name + "' has not yet been added!"
        return cls._conditions_dict[state_name]

    @classmethod
    def print_dict(cls):
        return '<Conditions %s>' % cls._conditions_dict

    @classmethod
    def initialize_worldstate(cls, worldstate):
        """Initialize the given worldstate with all known conditions and their current values."""
        for condition in cls._conditions_dict.values():
            condition.update_value(worldstate)



class Precondition(object):

    def __init__(self, condition, value, deviation=None):
        self._condition = condition
        self._value = value
        self._deviation = deviation

    def __str__(self):
        return '%s:%s=%s~%s' % (self.__class__.__name__, self._condition._state_name, self._value, self._deviation)

    def __repr__(self):
        return '<%s cond=%s value=%r dev=%s>' % (self.__class__.__name__, self._condition, self._value, self._deviation)

    def is_valid(self, worldstate):
        cond_value = worldstate.get_condition_value(self._condition)
        if self._deviation is None:
            return cond_value == self._value
        else:
            return abs(cond_value - self._value) <= self._deviation

    def apply(self, worldstate):
        # TODO: deviation gets lost in backwards planner
        worldstate.set_condition_value(self._condition, self._value)



class Effect(object):
    # TODO: integrate conditions beside memory
    # TODO: think about optional deviation

    def __init__(self, condition, new_value):
        self._condition = condition
        self._new_value = new_value

    def __str__(self):
        return '%s:%s=%s' % (self.__class__.__name__, self._condition._state_name, self._new_value)

    def __repr__(self):
        return '<%s cond=%s new_val=%s>' % (self.__class__.__name__, self._condition._state_name, self._new_value)

    def apply_to(self, worldstate):
        # TODO: remove me as I'm only for forward planning?
        worldstate.set_condition_value(self._condition, self._new_value)

    def matches_condition(self, worldstate):
        return worldstate.get_condition_value(self._condition) == self._new_value



class VariableEffect(object):

    def __init__(self, condition):
#        Effect.__init__(self, condition, None)
        self._condition = condition

    def __str__(self):
        return '%s:%s' % (self.__class__.__name__, self._condition._state_name)

    def __repr__(self):
        return '<%s cond=%s>' % (self.__class__.__name__, self._condition._state_name)

#     def apply_to(self, worldstate):
        # TODO: remove me as I'm only for forward planning?
#         worldstate.memory.set_value(self._condition, self._new_value)

    def matches_condition(self, worldstate):
        return self._is_reachable(worldstate.get_condition_value(self._condition))

    def _is_reachable(self, value):
        """Returns a Boolean whether this variable effect can reach the given value"""
        # TODO: change reachability from boolean to float
        raise NotImplementedError


class Goal(object):

    def __init__(self, preconditions):
        self._preconditions = preconditions

    def __repr__(self):
        return '<Goal preconditions=%s>' % self._preconditions

    def is_valid(self, worldstate):
        for precondition in self._preconditions:
            if not precondition.is_valid(worldstate):
                return False
        return True

    def apply_preconditions(self, worldstate):
        for precondition in self._preconditions:
            precondition.apply(worldstate)



class Action(object):

    def __init__(self, preconditions, effects):
        super(Action, self).__init__()
        self._preconditions = preconditions
        self._effects = effects

    def __str__(self):
        return self.__class__.__name__

    def __repr__(self):
        return '<%s preconditions=%s effects=%s>' % (self.__class__.__name__, self._preconditions, self._effects)

    def cost(self):
        return 1

    def run(self, next_worldstate):
        """
        next_worldstate: the worldstate that this action should lead to when run
        """
        raise NotImplementedError


    ## following for executor

    def is_valid(self, worldstate):
        """Return whether this action is applicable from the given worldstate on, i.e. all preconditions are."""
        for precondition in self._preconditions:
            if not precondition.is_valid(worldstate):
                return False
        return True


    ## following was for forward planner

    def apply_effects(self, worldstate):
        # TODO: remove me as I'm only for forward planning?
        for effect in self._effects:
            effect.apply_to(worldstate)


    ## following for backward planner

    def check_freeform_context(self):
        """Override to add context checks required to run this action that cannot be satisfied by the planner."""
        return True

    def has_satisfying_effects(self, worldstate, unsatisfied_conditions):
        """Return True if at least one of own effects matches unsatisfied_conditions."""
        for effect in self._effects:
            if effect._condition in unsatisfied_conditions: # TODO: maybe put this check into called method
                if effect.matches_condition(worldstate):
                    return True
        return False

    def apply_preconditions(self, worldstate, start_worldstate):
        """
        worldstate: the worldstate to apply this action's preconditions to
        start_worldstate: needed to let actions optimize their variable precondition parameters
        """
        # TODO: make required derivation of variable actions more obvious and fail-safe
        for precondition in self._preconditions:
            precondition.apply(worldstate)
        # let the action apply ad hoc preconditions for its variable effects
        var_effects = [effect for effect in self._effects if isinstance(effect, VariableEffect)]
        if len(var_effects) > 0:
            self.apply_adhoc_preconditions_for_vareffects(var_effects, worldstate, start_worldstate)

    def apply_adhoc_preconditions_for_vareffects(self, var_effects, worldstate, start_worldstate):
        """
        Let the action itself apply preconditions for its variable effects.

        Must be implemented if the action contains variable effects.
        """
        raise NotImplementedError



class ActionBag(object):

    def __init__(self):
        self._actions = set()

    def __repr__(self):
        return '<ActionBag %s>' % self._actions

    def add(self, action):
        self._actions.add(action)

    # regressive planning
    def generate_matching_actions(self, start_worldstate, node_worldstate):
        """Generator providing actions that might help between start_worldstate and current node_worldstate."""
        # TODO: This solution does not work when there are actions that produce an empty common_states_set and no valid action is considered - is this actually possible? the start_worldstate should contain every condition ever needed by an action or condition

        # check which conditions differ between start and current node
        unsatisfied_conditions_set = node_worldstate.get_unsatisfied_conditions(start_worldstate)

        # check which action might satisfy those conditions
        for action in self._actions:
            if action.has_satisfying_effects(node_worldstate, unsatisfied_conditions_set):
                print 'helping action: ', action
                yield action
            else:
                print 'helpless action: ', action


