
# All of these examples assume that the noise script is running to a
# localhost unis instance at 'http://localhost:8888'
# Start the noise script (located in the 'tools' directory):
#
# python noise.py http://localhost:8888
#
# The noise script will provide a metadata id which the client should ammend
# this script to reflect.
#
# In real-world applications, data will be provided by other clients at
# known periscope endpoints

# MID found in the url as below from the output of noise.py:
# --Posting http://localhost:8888/data/<mid> {'data': <value>, 'mid': <mid>}
mid = ''  # <---- Insert the MID provided by the noise script here


#---------------------------------
# Basic built-in data reading
#---------------------------------
from unis import Runtime
from unis.measurements import Last

def example1():
    rt = Runtime('http://localhost:8888')  # Create runtime

    try:
        md = next(rt.metadata.where({'id': mid})) # Get the metadata object
    except StopIteration:
        print("No metadata by that ID")
        return

    md.data.attachFunction(Last())  # Create a 'last' property for the data
                                    # which prints the last measurement

    # print each new value
    prev = md.data.last
    while True:
        new = md.data.last
        if prev != new:
            print(md.data.last)
            prev = new


#---------------------------------
# Creating a basic streaming function
#---------------------------------
from unis import Runtime
from unis.measurements import Function

class MyFunction(Function):
    def apply(self, value, ts):
        return self.prior + (value * 2)

def example2():
    rt = Runtime('http://localhost:8888')  # Create runtime
    
    try:
        md = next(rt.metadata.where({'id': mid})) # Get the metadata object
    except StopIteration:
        print("No metadata by that ID")
        return

    md.data.attachFunction(MyFunction(), 'half_sum')  # Create a 'half_sum'
                                                      # property for the data

    # print each new value
    prev = md.data.half_sum
    while True:
        new = md.data.half_sum
        if prev != new:
            print(md.data.half_sum)
            prev = new


#---------------------------------
# Adding state to function
#---------------------------------
from unis.measurements import Function

class MyConstantFive(Function):
    def __init__(self):
        super(MyConstantFive, self).__init__()
        self.value = 5
        self.ignored_values = []
    def apply(self, value, ts):
        self.ignored_values.append(value)
        return self.value


#---------------------------------
# Applying a post-processing function
#---------------------------------
from unis.measurements import Function

class MyMean(Function):
    def __init__(self):
        super(MyPostFunction, self).__init__()
        self.count = 0
    def apply(self, value, ts):
        self.count += 1
        return self.prior + value
    def postprocess(self, value):
        return value / self.count


# md.data.attachFunction(MyMean(), 'mean')
# print(md.data.mean)  # prints 3.3 when given [5, 1, 4]
# print(md.data.mean)  # prints 8 when given [8, 9, 7]
