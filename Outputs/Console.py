class Console(object):
    def __init__(self, config):
        print('Console initialized')
     
    def send(self, vals, batteryAPI):
        inverterDetails = vals.copy()
        inverterDetails.pop('Serial', None)

        for x, y in inverterDetails.items():
          print(x, y)