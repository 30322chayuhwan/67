from flask import Flask, request, jsonify
import random
import os

app = Flask(__name__)

# 유저들의 스탯 데이터를 임시 저장할 인메모리 DB
user_db = {}

# 직업별 기본 스탯
JOB_STATS = {
    "범생이": {"힘": 1, "민첩": 1, "지능": 5, "운": 1, "정신력": 2},
    "운동부": {"힘": 4, "민첩": 3, "지능": 1, "운": 1, "정신력": 1},
    "미술 실기생": {"힘": 2, "민첩": 1, "지능": 2, "운": 2, "정신력": 3}
}

@app.route('/select_job', methods=['POST'])
def select_job():
    req = request.get_json()
    user_id = req['userRequest']['user']['id']
    chosen_job = req['action']['params'].get('chosen_job', '범생이')
    
    user_db[user_id] = {
        "job": chosen_job,
        "stats": JOB_STATS[chosen_job].copy(),
        "inventory": []
    }
    
    stats = user_db[user_id]["stats"]
    response_text = (
        f"🎭 [{chosen_job}]을(를) 선택하셨습니다!\n\n"
        f"💪 힘: {stats['힘']} | ⚡ 민첩: {stats['민첩']}\n"
        f"🧠 지능: {stats['지능']} | 🍀 운: {stats['운']}\n"
        f"🧠 정신력: {stats['정신력']}\n\n"
        f"이제 교실 중앙에서 조사를 시작하세요."
    )
    return jsonify({
        "version": "2.0",
        "template": {"outputs": [{"simpleText": {"text": response_text}}]}
    })

@app.route('/escape', methods=['POST'])
def escape():
    req = request.get_json()
    user_id = req['userRequest']['user']['id']
    
    if user_id not in user_db:
        return jsonify({
            "version": "2.0",
            "template": {"outputs": [{"simpleText": {"text": "⚠️ 게임 시작 정보가 없습니다. 첫 블록부터 다시 시작해주세요."}}]}
        })
    
    player = user_db[user_id]
    job = player["job"]
    dice_roll = random.randint(1, 6)
    
    stat_bonus = 0
    stat_name = ""
    if job == "범생이":
        stat_name = "지능"
        stat_bonus = player["stats"]["지능"]
    elif job == "운동부":
        stat_name = "힘"
        stat_bonus = player["stats"]["힘"]
    elif job == "미술 실기생":
        stat_name = "정신력"
        stat_bonus = player["stats"]["정신력"]
        
    total_score = dice_roll + stat_bonus
    escape_cutoff = 6
    
    if total_score >= escape_cutoff:
        result_title = "🎉 탈출 성공!"
        result_text = (
            f"🎲 주사위: {dice_roll} + 🌟 {stat_name} 보너스: {stat_bonus}\n"
            f"📊 최종 판정 점수: {total_score} (기준: {escape_cutoff} 이상)\n\n"
            f"당신은 직업적 특성을 살려 잠긴 문을 열어젖혔습니다! "
            f"우당탕탕 소리와 함께 교실 문이 열리고 어두운 복도가 눈앞에 펼쳐집니다."
        )
    else:
        result_title = "💀 탈출 실패...?"
        result_text = (
            f"🎲 주사위: {dice_roll} + 🌟 {stat_name} 보너스: {stat_bonus}\n"
            f"📊 최종 판정 점수: {total_score} (기준: {escape_cutoff} 이상)\n\n"
            f"아무리 애를 써봐도 문은 꿈쩍도 하지 않습니다. "
            f"그때, 교실 뒷문 아래로 검은 그림자가 천천히 스며들기 시작합니다..."
        )

    # 탈출 블록 실행 완료 시 데이터 즉시 초기화
    user_db.pop(user_id, None)
    
    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "basicCard": {
                        "title": result_title,
                        "description": result_text,
                        "buttons": [
                            {
                                "action": "block",
                                "label": "다음 단계로 진행" if total_score >= escape_cutoff else "처음부터 다시 도전",
                                "blockId": "여기에_이동할_블록_ID_입력"
                            }
                        ]
                    }
                }
            ]
        }
    })

if __name__ == '__main__':
    # 렌더 환경에서 제공하는 포트를 자동으로 감지하여 실행합니다.
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
