import os, urllib.request, json

token = os.environ.get("RAILWAY_API_TOKEN", "")
project_id = os.environ.get("RAILWAY_PROJECT_ID", "520adb72-b1f4-4021-8c4b-21ca81f8a901")

query = {"query": 'mutation { serviceCreate(input: {projectId: "%s", name: "Postgres", templateId: "postgres"}) { id name } }' % project_id}
req = urllib.request.Request("https://backboard.railway.com/graphql/v2")
req.add_header("Authorization", "Bearer %s" % token)
req.add_header("Content-Type", "application/json")
resp = urllib.request.urlopen(req, json.dumps(query).encode())
print(resp.read().decode())
