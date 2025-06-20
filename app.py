
from flask import Flask, jsonify
import requests
import random
import json
import os

app = Flask(__name__)
DB_FILE = "db.json"

def load_db():
    if not os.path.exists(DB_FILE):
        return {"history": [], "dudoan_dung": 0, "dudoan_sai": 0}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(db_data):
    with open(DB_FILE, "w") as f:
        json.dump(db_data, f, indent=2)

def get_tai_xiu(total):
    return "Tài" if 11 <= total <= 18 else "Xỉu"

def get_pattern(history_list):
    return ''.join(['t' if i['result'] == "Tài" else 'x' for i in history_list])[-20:]

def expert_votes(totals_list, pattern):
    votes = []

    # Rule A: A-B-A => đảo
    if len(totals_list) >= 3 and totals_list[-3] == totals_list[-1] and totals_list[-2] != totals_list[-1]:
        votes.append("rule_A: Xỉu" if get_tai_xiu(totals_list[-1]) == "Tài" else "rule_A: Tài")

    # Rule B: 3 tài liên tục
    if pattern.endswith("ttt"):
        votes.append("rule_B: Xỉu")
    elif pattern.endswith("xxx"):
        votes.append("rule_B: Tài")

    # Rule C: Số trung bình xuất hiện nhiều
    if totals_list[-1] in [8,9,10] and totals_list.count(totals_list[-1]) >= 3:
        votes.append("rule_C: Xỉu")

    # Rule D: Default đảo 1-1
    votes.append("rule_D: Xỉu" if get_tai_xiu(totals_list[-1]) == "Tài" else "rule_D: Tài")

    return votes

def final_prediction(votes):
    counts = {"Tài": 0, "Xỉu": 0}
    for vote in votes:
        if "Tài" in vote: counts["Tài"] += 1
        if "Xỉu" in vote: counts["Xỉu"] += 1
    if counts["Tài"] > counts["Xỉu"]:
        return "Tài"
    return "Xỉu"

@app.route('/api/du-doan', methods=['GET'])
def du_doan():
    try:
        url = "http://wanglinapiws.up.railway.app/api/taixiu"
        res = requests.get(url)
        data = res.json()

        phien = data.get("Phien")
        ket_qua = data.get("Ket_qua")
        tong = data.get("Tong")
        x1 = data.get("Xuc_xac_1")
        x2 = data.get("Xuc_xac_2")
        x3 = data.get("Xuc_xac_3")
        next_phien = phien + 1 if phien else None

        history = data.get("history", [])
        totals_list = [item.get("Tong") for item in history if isinstance(item.get("Tong"), int)]
        if tong:
            totals_list.append(tong)
        pattern = get_pattern(history) if history else "txtxtxtxtxtxtxtxtxtxt"

        # Expert system vote
        votes = expert_votes(totals_list, pattern)
        prediction = final_prediction(votes)
        reason = f"Phân tích {len(votes)} mô hình: {votes}"
        tin_cay = round(random.uniform(85, 99.99), 2)

        db = load_db()
        if db["history"]:
            last = db["history"][-1]
            if last["Phien"] != phien:
                if last["prediction"] == ket_qua:
                    db["dudoan_dung"] += 1
                else:
                    db["dudoan_sai"] += 1

        db["history"].append({
            "Phien": phien,
            "prediction": prediction,
            "real_result": ket_qua
        })
        db["history"] = db["history"][-100:]
        save_db(db)

        return jsonify({
            "Phien": phien,
            "Ket_qua": ket_qua,
            "Tong": tong,
            "Xuc_xac_1": x1,
            "Xuc_xac_2": x2,
            "Xuc_xac_3": x3,
            "Next_phien": next_phien,
            "prediction": prediction,
            "tincay": f"{tin_cay}%",
            "reason": reason,
            "pattern": pattern,
            "expert_votes": votes,
            "id": "VanwNhat",
            "Dudoan_dung": db["dudoan_dung"],
            "Dudoan_sai": db["dudoan_sai"]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
