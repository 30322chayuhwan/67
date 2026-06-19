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

# 🎭 직업별로 출력할 카카오톡 메시지를 미리 하나하나 다 정의해둡니다!
# 나중에 문구나 이모지를 바꾸고 싶다면 여기만 수정하시면 됩니다.
JOB_RESPONSES = {
    "범생이": (
        "🤓 [범생이]을(를) 선택하셨습니다!\n\n"
        "💪 힘: 1 | ⚡ 민첩: 1\n"
        "🧠 지능: 5 | 🍀 운: 1\n"
        "🛡️ 정신력: 2\n\n"
        "가방끈은 길지만 몸 쓰는 일엔 쥐약입니다.\n"
        "이제 교실 중앙에서 조사를 시작하세요."
    ),
    "운동부": (
        "🏃 [운동부]을(를) 선택하셨습니다!\n\n"
        "💪 힘: 4 | ⚡ 민첩: 3\n"
        "🧠 지능: 1 | 🍀 운: 1\n"
        "🛡️ 정신력: 1\n\n"
        "머리보다 몸이 먼저 반응하는 타입입니다!\n"
        "이제 교실 중앙에서 조사를 시작하세요."
    ),
    "미술 실기생": (
        "🎨 [미술 실기생]을(를) 선택하셨습니다!\n\n"
        "💪 힘: 2 | ⚡ 민첩: 1\n"
        "🧠 지능: 2 | 🍀 운: 2\n"
        "🛡️ 정신력: 3\n\n"
        "섬세한 감각과 남다른 정신력을 가졌습니다.\n"
        "이제 교실 중앙에서 조사를 시작하세요."
    )
}

@app.route('/select_job', methods=['POST'])
def select_job():
    """ [블록 2: 직업 선택] 1:1 매칭 텍스트 직접 출력 버전 """
    req = request.get_json()
    user_request = req.get('userRequest', {})
    user_info = user_request.get('user', {})
    user_id = user_info.get('id') or user_info.get('plusfriendUserKey') or user_request.get('plusfriend', {}).get('id', 'test_user')
    
    # 유저가 보낸 발화에서 따옴표, 공백 제거 (예: "🏃 운동부" -> "운동부")
    utterance = user_request.get('utterance', '').strip().replace('"', '').replace("'", "")
    
    # 🔍 입력받은 글자 그대로 직업을 결정합니다.
    chosen_job = "범생이" # 찾지 못했을 때를 대비한 기본값
    for job in JOB_STATS.keys():
        if job in utterance:
            chosen_job = job
            break
            
    # ⚠️ 중요: 내부 유저 데이터 DB(스탯, 인벤토리)는 기존대로 정확하게 초기화합니다.
    user_db[user_id] = {
        "job": chosen_job,
        "stats": JOB_STATS[chosen_job].copy(),
        "inventory": []
    }
    
    # 🎯 [핵심] 상단에 하나하나 적어둔 직업별 텍스트를 그대로 가져옵니다!
    response_text = JOB_RESPONSES.get(chosen_job, JOB_RESPONSES["범생이"])

    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": response_text}}],
            "quickReplies": [
                {"action": "block", "label": "🔦 조사 시작하기", "blockId": "6a1ce5d3568d272d8eb2365b"}
            ]
        }
    })
@app.route('/roll', methods=['POST'])
def roll_check():
    """ [범용 주사위 판정 시스템] 장소별 보상 추가 버전 """
    req = request.get_json()
    user_request = req.get('userRequest', {})
    user_info = user_request.get('user', {})
    user_id = user_info.get('id') or user_info.get('plusfriendUserKey') or user_request.get('plusfriend', {}).get('id', 'test_user')
    
    if user_id not in user_db:
        return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": "⚠️ 플레이 기록이 없습니다. 처음부터(직업 선택) 다시 시작해주세요."}}]}})
        
    player = user_db[user_id]
    
    # 카카오 빌더에서 넘겨받는 데이터들
    client_extra = req['action'].get('clientExtra', {})
    stat_type = client_extra.get('stat', '운')             
    difficulty = int(client_extra.get('dc', 5))            
    success_block = client_extra.get('success_block_id')   
    fail_block = client_extra.get('fail_block_id')         
    location = client_extra.get('location', '일반')  # 👈 새로 추가됨! 현재 장소를 받아옵니다.

    # 1. 6면체 주사위 굴리기
    dice_roll = random.randint(1, 6)
    
    # 2. 스탯 보너스
    stat_bonus = player["stats"].get(stat_type, 0)
    
    # 3. 🎯 아이템 착용(소지) 효과 적용
    item_bonus = 0
    if stat_type == "힘" and "빗자루" in player["inventory"]:
        item_bonus += 1
    if stat_type == "정신력" and "에너지바" in player["inventory"]:
        item_bonus += 1

    # 4. 최종 점수 계산
    total_score = dice_roll + stat_bonus + item_bonus
    is_success = total_score >= difficulty

    # 5. 결과 처리
    acquired_item = None # 이번 턴에 얻은 아이템을 기록할 변수

    if is_success:
        # 🎉 성공했을 때 장소별 아이템 지급 로직
        if location == "창고" and "빗자루" not in player["inventory"]:
            player["inventory"].append("빗자루")
            acquired_item = "빗자루"
            
        elif location == "교무실" and "에너지바" not in player["inventory"]:
            player["inventory"].append("에너지바")
            acquired_item = "에너지바"
            
        elif location == "동아리실" and "유물" not in player["inventory"]:
            # 🍀 운 스탯이 7 이상일 때만 유물 획득!
            if player["stats"].get("운", 0) >= 7:
                player["inventory"].append("유물")
                acquired_item = "유물"

        title = "🎉 판정 성공!"
        desc = f"📊 [{stat_type}] 판정 (목표: {difficulty})\n🎲 주사위: {dice_roll}\n💪 스탯: +{stat_bonus}\n"
        if item_bonus > 0: desc += f"🎒 아이템 시너지: +{item_bonus}\n"
        desc += f"🔥 최종 점수: {total_score}\n\n성공 스토리가 이어집니다."
        
        # 아이템을 얻었다면 문구 추가
        if acquired_item:
            desc += f"\n\n🎁 앗! 무언가 발견했습니다!\n[ {acquired_item} ]을(를) 획득했습니다!"

        next_block = success_block
        button_label = "다음 스토리 진행"

    else:
        # 💀 실패했을 때는 이제 아무것도 주지 않습니다.
        title = "💀 판정 실패..."
        desc = f"📊 [{stat_type}] 판정 (목표: {difficulty})\n🎲 주사위: {dice_roll}\n💪 스탯: +{stat_bonus}\n"
        if item_bonus > 0: desc += f"🎒 아이템 시너지: +{item_bonus}\n"
        desc += f"🔥 최종 점수: {total_score}\n\n예기치 못한 위험이 닥칩니다."
        
        next_block = fail_block
        button_label = "실패 결과 확인"

    # 카드 출력 반환
    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [{
                "basicCard": {
                    "title": title,
                    "description": desc,
                    "buttons": [{"action": "block", "label": button_label, "blockId": next_block if next_block else "초기블록"}]
                }
            }]
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
