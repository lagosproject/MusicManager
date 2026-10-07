import json

class Utilities:
    def saveResponse(response, filename):
        app_json = json.dumps(response)
        f = open(filename, "w")

        f.write(app_json)
        f.close()

    def normalSave(response, filename):
        f = open(filename, "w")
        f.write(response)
        f.close()
        