from operator import itemgetter
import queue
import copy
import re

class IllegalPatternError(Exception):
    pass

# define the pattern class that stores representation of the pattern
class pattern:
    def __init__(self):
        self.len = 0
        self.pattern = []

    def getPatternLen(self):
        return self.len

    def getPattern(self):
        return self.pattern

    def updatePattern(self, component_type, component_len):
        self.pattern.append(component_type)
        if component_type == 'f':
            self.pattern.append(component_len)
            self.len += len(component_len)
        elif component_type == 'd' or component_type == 'L':
            self.pattern.append(component_len)
            self.len += component_len

    def pop(self):
        if len(self.pattern)>=2:
            component_type, component_len = self.pattern[-2:]
            self.pattern = self.pattern[:-2]
            if component_type == 'f':
                self.len -= len(component_len)
            elif component_type == 'd' or component_type == 'L':
                self.len -= component_len


class ConvertStrToPatternList:
    """
        Convert a pattern string to a list of potential patterns
    """
    def __init__(self, pattern_str):
        self.pattern_str = pattern_str
        self.pattern_list = []

    def _str_parser(self):
        """Parse string into different components of patterns
        Returns:
            parsed_pattern_str: a list of strings that are the components of the pattern
            e.g. pattern_str='[ZS]d(2,5)L(3), parsed_pattern_str=['[ZS]', 'd(2,5)', 'L(3)']'
        """
        try:
            parsed_pattern_str = []
            pattern_str = self.pattern_str
            while len(pattern_str) > 0:
                # match fixed string
                if re.match(r"\[([A-Z0-9\-]*)\]", pattern_str):
                    pattern = re.match(r"\[([A-Z0-9\-]*)\]", pattern_str).group()
                    parsed_pattern_str.append(pattern)
                    pattern_str = pattern_str[len(pattern):]
                # match digit string
                elif re.match(r"d\([0-9\,]*\)", pattern_str):
                    pattern = re.match(r"d\([0-9\,]*\)", pattern_str).group()
                    parsed_pattern_str.append(pattern)
                    pattern_str = pattern_str[len(pattern):]
                # match letter string
                elif re.match(r"L\([0-9\,]*\)", pattern_str):
                    pattern = re.match(r"L\([0-9\,]*\)", pattern_str).group()
                    parsed_pattern_str.append(pattern)
                    pattern_str = pattern_str[len(pattern):]
                # illegal pattern
                else:
                    raise IllegalPatternError
        # exception handling
        except IllegalPatternError:
            print("Pattern is illegal!")
            return []

        return parsed_pattern_str



    def _component_converter(self, parsed_pattern_str):
        """Convert the parsed_pattern_str to a list of components
        Args:
            parsed_pattern_str: a list that represents components of the pattern
        Returns:
            component_list: a list, each element is a dictionary that represents a component of the pattern
            e.g parsed_pattern_str = ['[ZS]', 'd(2,5)', 'L(3)'], returns component_list = [{'f':'ZS'}, {'d':[2,3,4,5]}, {'L':[2]}]
        """

        if len(parsed_pattern_str) == 0:
            return []

        component_list = []
        try:
            for block in parsed_pattern_str:
                tmp_dict = {}
                if block[0] == '[' and block[-1] == ']':
                    tmp_dict['f'] = block[1:-1]
                elif block[:2] == 'L(' and block[-1] == ')':
                    len_str = block[2:-1].split(',')
                    # if there are illegal characters here, or multiple comma, or start > end
                    len_range = [int(l) for l in len_str]
                    if len(len_range) == 1:
                        tmp_dict['L'] = len_range
                    elif len(len_range) == 2:
                        start, end = len_range
                        if start > end:
                            raise IllegalPatternError
                        else:
                            tmp_dict['L'] = list(range(start, end+1))
                elif block[:2] == 'd(' and block[-1] == ')':
                    len_str = block[2:-1].split(',')
                    len_range = [int(l) for l in len_str]
                    if len(len_range) == 1:
                        tmp_dict['d'] = len_range
                    elif len(len_range) == 2:
                        start, end = len_range
                        if start > end:
                            raise IllegalPatternError
                        else:
                            tmp_dict['d'] = list(range(start, end+1))
                else:
                    raise IllegalPatternError
                    return []
                component_list.append(tmp_dict)
        except IllegalPatternError:
            print("Pattern is illegal!")
            return []

        return component_list


    def _bfs_pattern(self, component_list):
        """bfs the component_list and get all the potential patterns
        Args:
            component_list: a list of all the components of the pattern
        Returns:
            potential_pattern: a list of all the potential patterns
        """
        root = component_list[0]
        pattern_queue = queue.Queue()
        # insert the first element into the queue
        for key, value in root.items():
            if isinstance(value, str):
                pattern_tmp = pattern()
                pattern_tmp.updatePattern(key, value)
                pattern_queue.put(pattern_tmp)
            elif isinstance(value, list):
                for item in value:
                    pattern_tmp = pattern()
                    pattern_tmp.updatePattern(key, item)
                    pattern_queue.put(pattern_tmp)

        # bfs
        next_queue = queue.Queue()
        for block in component_list[1:]:
            while not pattern_queue.empty():
                front = pattern_queue.get()
                for key, value in block.items():
                    if isinstance(value, str):
                        front.updatePattern(key, value)
                        next_queue.put(copy.deepcopy(front))
                        front.pop()
                    elif isinstance(value, list):
                        for item in value:
                            front.updatePattern(key, item)
                            next_queue.put(copy.deepcopy(front))
                            front.pop()
            pattern_queue.queue = copy.deepcopy(next_queue.queue)
            next_queue = queue.Queue()

        potential_pattern = list(pattern_queue.queue)

        self.pattern_list = potential_pattern


    def process(self):
        """
            ConvertStrToPatternList pipeline
        """
        parsed_pattern_str = self._str_parser()
        component_list = self._component_converter(parsed_pattern_str)
        self._bfs_pattern(component_list)

    def get_pattern_list(self):
        """
            Get pattern list
        """
        return self.pattern_list

class PatternMatching:
    def __init__(self, pid, potential_list):
        self.pid = pid
        self.potential_list = potential_list
        self.potential_result = []

    @staticmethod
    def _char_to_letter(ch):
        # rules to convert to letters
        switcher = {
            '0': 'D',
            '1': 'I',
            '2': 'Z',
            '5': 'S',
            '6': 'G',
            '7': 'T',
            '8': 'B',
        }
        return switcher.get(ch, ch)


    @staticmethod
    def _char_to_digit(ch):
        # rules to convert to digits
        switcher = {
            'B': '8',
            'D': '0',
            'G': '6',
            'I': '1',
            'J': '1',
            'O': '0',
            'S': '5',
            'T': '7',
            'Z': '2',
        }
        return switcher.get(ch, ch)

    def _convert_string(self, pattern):
        """
            Convert self.pid according to pattern
            Args: pattern
            Returns: a dictionary, {'change_bits':the number of change characters, 'converted_pid':the converted string}
        """
        start_pos = 0
        pid_pos = 0
        change_bits = 0
        converted_pid = ""
        pattern_list = pattern.getPattern()

        while start_pos < len(pattern_list):
            component_type = pattern_list[start_pos]
            component_len = pattern_list[start_pos+1]
            if component_type == 'f':
                converted_pid += component_len
                for i in range(len(component_len)):
                    if self.pid[pid_pos+i] != component_len[i]:
                        change_bits += 1
                pid_pos += len(component_len)
            elif component_type == 'L':
                for i in range(component_len):
                    converted_char = self._char_to_letter(self.pid[pid_pos+i])
                    if converted_char != self.pid[pid_pos+i]:
                        change_bits += 1
                    converted_pid += converted_char
                pid_pos += component_len
            elif component_type == 'd':
                for i in range(component_len):
                    converted_char = self._char_to_digit(self.pid[pid_pos+i])
                    if converted_char != self.pid[pid_pos+i]:
                        change_bits += 1
                    converted_pid += converted_char
                pid_pos += component_len
            start_pos += 2

        return {'change_bits': change_bits, 'converted_pid': converted_pid}


    def process(self):
        """
            pattern matching pipeline, match pattern to the pid and convert the pid based on the rules
        """
        # filter out the patterns that don't match the pid length
        removed_pattern = []
        for pattern in self.potential_list:
            if pattern.getPatternLen() != len(self.pid):
                removed_pattern.append(pattern)
        potential_pattern = [pattern for pattern in self.potential_list if pattern not in removed_pattern]

        # convert the pid according to the patterns availabe, sort the potential results by number of changes in ascending order
        potential_result = []
        for pattern in potential_pattern:
            potential_result.append(self._convert_string(pattern))

        potential_result = sorted(potential_result, key=itemgetter('change_bits'))
        self.potential_result = potential_result

    def get_potential_result(self):
        """
            get potential result
        """
        return self.potential_result

'''
potential_pattern = pattern_parser(pattern_str)
if len(potential_pattern) == 0:
    print("No potential pattern found")
result = pattern_matching("251Z34566H", potential_pattern)
print(result)
if len(result) == 0:
    print("No matched result")
else:
    print(result[0]['converted_pid'])
'''
