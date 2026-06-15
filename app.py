from flask import Flask, request, jsonify
import random
import os

app = Flask(__name__)

# 유저들의 게임 상태(스탯, 인벤토리)를 저장할 인메모리 DB
user_db = {}

# 직업별 초기 스탯 정의
JOB_STATS = {
    "범생이": {"힘": 1, "민첩": 1, "지능": 5, "운": 1, "정신력": 2},
    "운동부": {"힘": 4, "민첩": 3, "지능": 1, "운": 1, "정신력": 1},
    "미술 실기생": {"힘": 2, "민첩": 1, "지능": 2, "운": 2, "정신력": 3}
}

@app.route('/select_job', methods=['POST'])
def select_job():
    """ [블록 2: 직업 선택] 유저 세션 생성 및 스탯 부여 """
    req = request.get_json()
    # 카카오톡이 주는 유저 고유 키를 여러 경로로 안전하게 탐색
    user_request = req.get('userRequest', {})
    user_info = user_request.get('user', {})
    
    # id가 없으면 plusfriendUserKey나 가짜 고유값을 만들어서라도 매칭 성공시킴
    user_id = user_info.get('id') or user_info.get('plusfriendUserKey') or user_request.get('plusfriend', {}).get('id', 'test_user')
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


@app.route('/add_item', methods=['POST'])
def add_item():
    """ [아이템 파밍] 인벤토리에 아이템을 추가함 """
    req = request.get_json()
    user_id = req['userRequest']['user']['id']
    
    if user_id not in user_db:
        return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": "⚠️ 게임 정보가 없습니다. 처음부터 시작해주세요."}}]}})
    
    client_extra = req['action'].get('clientExtra', {})
    item_name = client_extra.get('item_name', '의문의 물건')
    next_block_id = client_extra.get('next_block_id')
    
    if item_name not in user_db[user_id]["inventory"]:
        user_db[user_id]["inventory"].append(item_name)
        msg = f"🎒 소지품에 [{item_name}]을(를) 추가했습니다!"
    else:
        msg = f"🎒 이미 [{item_name}]을(를) 가지고 있습니다."
        
    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "basicCard": {
                        "title": "아이템 획득 성공",
                        "description": msg,
                        "buttons": [
                            {"action": "block", "label": "계속 탐색하기", "blockId": next_block_id}
                        ]
                    }
                }
            ]
        }
    })


@app.route('/roll', methods=['POST'])
def roll_check():
    """ [범용 주사위 판정 시스템] 대성공/대실패 로직 제거 버전 """
    req = request.get_json()
    user_request = req.get('userRequest', {})
    user_info = user_request.get('user', {})
    user_id = user_info.get('id') or user_info.get('plusfriendUserKey') or user_request.get('plusfriend', {}).get('id', 'test_user')
    
    if user_id not in user_db:
        return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": "⚠️ 플레이 기록이 없습니다. 처음부터 시작해주세요."}}]}})
        
    player = user_db[user_id]
    
    client_extra = req['action'].get('clientExtra', {})
    stat_type = client_extra.get('stat', '운')             
    difficulty = int(client_extra.get('dc', 5))           
    success_block = client_extra.get('success_block_id')   
    fail_block = client_extra.get('fail_block_id')         
    is_final = client_extra.get('is_final', False)         

    # 1. 6면체 주사위 굴리기 (1~6 랜덤)
    dice_roll = random.randint(1, 6)
    
    # 2. 스탯 보너스
    stat_bonus = player["stats"].get(stat_type, 0)
    
   # 3. 아이템 보너스
    item_bonus = 0
    if stat_type == "힘":
        if "야구 배트" in player["inventory"]:
            item_bonus = 2
        elif "빗자루" in player["inventory"]:
            item_bonus = 1
    elif stat_type == "정신력" and "오컬트 부적" in player["inventory"]:
        item_bonus = 2

    # 4. 최종 점수 계산 및 판정
    total_score = dice_roll + stat_bonus + item_bonus
    is_success = total_score >= difficulty

    # 5. 결과 화면 출력 조립
    if is_success:
        title = "🎉 판정 성공!"
        desc = (
            f"📊 판정 종류: [{stat_type}] 판정 (목표치: {difficulty} 이상)\n"
            f"🎲 주사위 결과: {dice_roll}\n"
            f"💪 캐릭터 스탯 보너스: +{stat_bonus}\n"
        )
        if item_bonus > 0:
            desc += f"🎒 아이템 시너지 보너스: +{item_bonus}\n"
        desc += f"🔥 최종 결산 점수: {total_score}\n\n성공 스토리가 이어집니다."
        
        next_block = success_block
        button_label = "다음 스토리 진행"
    else:
        title = "💀 판정 실패..."
        desc = (
            f"📊 판정 종류: [{stat_type}] 판정 (목표치: {difficulty} 이상)\n"
            f"🎲 주사위 결과: {dice_roll}\n"
            f"💪 캐릭터 스탯 보너스: +{stat_bonus}\n"
        )
        if item_bonus > 0:
            desc += f"🎒 아이템 시너지 보너스: +{item_bonus}\n"
        desc += f"🔥 최종 결산 점수: {total_score}\n\n예기치 못한 위험이 닥칩니다."
        
        next_block = fail_block
        button_label = "실패 결과 확인"

    # 최종 탈출/엔딩 블록일 때 플레이어 세션 삭제
    if is_final:
        user_db.pop(user_id, None)
        desc += "\n\n⚠️ 게임이 마무리되어 세션 기록이 안전하게 초기화되었습니다."

    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "basicCard": {
                        "title": title,
                        "description": desc,
                        "buttons": [
                            {
                                "action": "block",
                                "label": button_label,
                                "blockId": next_block if next_block else "초기_오프닝_블록_ID"
                            }
                        ]
                    }
                }
            ]
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
