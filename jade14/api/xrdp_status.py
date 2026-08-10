import subprocess, json
def get_xrdp_status():
    try:
        status = subprocess.check_output(["systemctl","is-active","xrdp"],text=True).strip()
        sessions = subprocess.check_output(["loginctl","list-sessions","--no-legend"],text=True).strip().split("\n")
        session_list=[]
        for s in sessions:
            if not s.strip(): continue
            parts=s.split()
            session_list.append({"id":parts[0],"user":parts[1],"seat":parts[2] if len(parts)>2 else "n/a"})
        return json.dumps({"status":status,"sessions":session_list})
    except Exception as e:
        return json.dumps({"error":str(e)})
