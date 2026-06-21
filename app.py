from flask import Flask, request, jsonify
import random
import os

app = Flask(__name__)

# 유저들의 게임 상태(스탯, 인벤토리, 체력)를 저장할 인메모리 DB
user_db = {}

JOB_STATS = {
    "범생이": {"힘": 1, "민첩": 1, "지능": 5, "운": 1, "정신력": 2},
    "운동부": {"힘": 4, "민첩": 3, "지능": 1, "운": 1, "정신력": 1},
    "미술 실기생": {"힘": 2, "민첩": 1, "지능": 2, "운": 2, "정신력": 3}
}

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
        "섬세한 감각 and 남다른 정신력을 가졌습니다.\n"
        "이제 교실 중앙에서 조사를 시작하세요."
    )
}

def get_clean_user_id(req):
    user_request = req.get('userRequest', {})
    user_info = user_request.get('user', {})
    plusfriend = user_request.get('plusfriend', {})
    
    uid = (
        user_info.get('id') or 
        user_info.get('plusfriendUserKey') or 
        plusfriend.get('id') or 
        'test_user'
    )
    return str(uid) 

@app.route('/select_job', methods=['POST'])
def select_job():
    req = request.get_json()
    user_id = get_clean_user_id(req) 
    
    utterance = req.get('userRequest', {}).get('utterance', '').strip().replace('"', '').replace("'", "")
    action = req.get('action', {})
    
    chosen_job = None
    for job in JOB_STATS.keys():
        if job in utterance:
            chosen_job = job
            break
            
    if not chosen_job:
        chosen_job = action.get('params', {}).get('chosen_job') or action.get('clientExtra', {}).get('chosen_job', '범생이')
    
    # 🎯 내부 DB에 저장할 때 최대 체력(hp: 3)을 부여합니다!
    user_db[user_id] = {
        "job": chosen_job,
        "stats": JOB_STATS[chosen_job].copy(),
        "inventory": [],
        "hp": 3  # 최대 체력 3
    }
    
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
    """ [범용 주사위 판정 시스템] """
    req = request.get_json()
    user_id = get_clean_user_id(req) 
    
    if user_id not in user_db:
        return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": "⚠️ 플레이 기록이 없습니다. 처음부터 다시 시작해주세요."}}]}})
        
    player = user_db[user_id]
    client_extra = req['action'].get('clientExtra', {})
    stat_type = client_extra.get('stat', '운')              
    difficulty = int(client_extra.get('dc', 5))            
    success_block = client_extra.get('success_block_id')   
    fail_block = client_extra.get('fail_block_id')         
    location = client_extra.get('location', '일반')  
    
    # 🎯 빌더에서 "is_danger": "true"를 보냈는지 확인합니다.
    is_danger = client_extra.get('is_danger', 'false').lower() == 'true'

    dice_roll = random.randint(1, 6)
    stat_bonus = player["stats"].get(stat_type, 0)
    
    item_bonus = 0
    if stat_type == "힘" and "빗자루" in player["inventory"]: item_bonus += 1
    if stat_type == "정신력" and "에너지바" in player["inventory"]: item_bonus += 1

    total_score = dice_roll + stat_bonus + item_bonus
    is_success = total_score >= difficulty
    acquired_item = None 

    if is_success:
        if location == "창고" and "빗자루" not in player["inventory"]:
            player["inventory"].append("빗자루")
            acquired_item = "빗자루"
        elif location == "교무실" and "에너지바" not in player["inventory"]:
            player["inventory"].append("에너지바")
            acquired_item = "에너지바"
        elif location == "동아리실" and "유물" not in player["inventory"]:
            player["inventory"].append("유물")
            acquired_item = "유물"

        title = "🎉 판정 성공!"
        desc = f"📊 [{stat_type}] 판정 (목표: {difficulty})\n🎲 주사위: {dice_roll}\n💪 스탯: +{stat_bonus}\n"
        if item_bonus > 0: desc += f"🎒 아이템 시너지: +{item_bonus}\n"
        desc += f"🔥 최종 점수: {total_score}\n\n성공 스토리가 이어집니다."
        
        if acquired_item:
            desc += f"\n\n🎁 앗! 무언가 발견했습니다!\n[ {acquired_item} ]을(를) 획득했습니다!"

        next_block = success_block
        button_label = "다음 스토리 진행"

    else:
        # 실패 처리
        if is_danger:
            # 위험한 판정에서 실패했을 때만 체력 감소!
            player["hp"] -= 1
            if player["hp"] <= 0:
                del user_db[user_id]
                title = "💀 게임 오버..."
                desc = (
                    f"📊 [{stat_type}] 판정 실패\n"
                    f"🔥 앗! 치명상을 입었습니다.\n\n"
                    f"체력이 0이 되어 쓰러졌습니다...\n"
                    f"모든 소지품을 잃고 처음으로 돌아갑니다."
                )
                next_block = "6a26283f95b9c60df67a5932" 
                button_label = "처음부터 다시 시작"
            else:
                title = "⚠️ 판정 실패 및 부상!"
                desc = f"📊 [{stat_type}] 판정 (목표: {difficulty})\n🎲 주사위: {dice_roll}\n💪 스탯: +{stat_bonus}\n"
                if item_bonus > 0: desc += f"🎒 아이템 시너지: +{item_bonus}\n"
                desc += f"🔥 최종 점수: {total_score}\n\n위험에 노출되어 💔체력을 1 잃었습니다! (남은 체력: {player['hp']}/3)"
                next_block = fail_block
                button_label = "실패 결과 확인"
        else:
            # 체력이 깎이지 않는 일반적인 실패
            title = "💀 판정 실패..."
            desc = f"📊 [{stat_type}] 판정 (목표: {difficulty})\n🎲 주사위: {dice_roll}\n💪 스탯: +{stat_bonus}\n"
            if item_bonus > 0: desc += f"🎒 아이템 시너지: +{item_bonus}\n"
            desc += f"🔥 최종 점수: {total_score}\n\n예기치 못한 위험이 닥칩니다."
            next_block = fail_block
            button_label = "실패 결과 확인"

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

@app.route('/add_injury', methods=['POST'])
def add_injury():
    """ [신규 블록] 주사위 없이 그냥 함정을 밟았을 때 강제로 부상을 부여 """
    req = request.get_json()
    user_id = get_clean_user_id(req) 
    
    if user_id not in user_db:
        return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": "⚠️ 플레이 기록이 없습니다."}}]}})
        
    player = user_db[user_id]
    player["hp"] -= 1
    
    client_extra = req['action'].get('clientExtra', {})
    next_block = client_extra.get('next_block_id')

    if player["hp"] <= 0:
        del user_db[user_id]
        title = "💀 게임 오버..."
        desc = "치명적인 상처를 입고 쓰러졌습니다...\n모든 데이터가 초기화됩니다."
        button_block = "6a26283f95b9c60df67a5932"
        button_label = "처음부터 다시 시작"
    else:
        title = "⚠️ 함정 발동! 부상을 입었습니다."
        desc = f"아야! 예기치 못한 피해를 입었습니다.\n\n💔 체력 -1 (남은 체력: {player['hp']}/3)"
        button_block = next_block
        button_label = "스토리 계속하기"

    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [{
                "basicCard": {
                    "title": title,
                    "description": desc,
                    "buttons": [{"action": "block", "label": button_label, "blockId": button_block if button_block else "초기블록"}]
                }
            }]
        }
    })

@app.route('/check_status', methods=['POST'])
def check_status():
    req = request.get_json()
    user_id = get_clean_user_id(req) 
    
    if user_id not in user_db:
        return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": "⚠️ 아직 게임을 시작하지 않았습니다. 직업을 먼저 선택해 주세요!"}}]}})
        
    player = user_db[user_id]
    stats = player["stats"]
    inventory = player["inventory"]
    
    job_emojis = {"범생이": "🤓", "운동부": "🏃", "미술 실기생": "🎨"}
    job_emoji = job_emojis.get(player["job"], "🎭")
    
    inventory_text = ", ".join([f"[{i}]" for i in inventory]) if inventory else "비어 있음"
    
    active_effects = []
    if "빗자루" in inventory: active_effects.append("🧹 빗자루 (힘 판정 시 +1)")
    if "에너지바" in inventory: active_effects.append("🍫 에너지바 (정신력 판정 시 +1)")
    if "유물" in inventory: active_effects.append("✨ 유물 (신비한 기운이 맴돕니다)")
    
    effects_text = "\n".join(active_effects) if active_effects else "적용 중인 효과 없음"

    response_text = (
        f"{job_emoji} [{player['job']}]의 현재 상태\n"
        f"──────────────────\n"
        f"❤️ 체력: {player.get('hp', 3)} / 3\n"
        f"──────────────────\n"
        f"💪 힘: {stats['힘']} | ⚡ 민첩: {stats['민첩']}\n"
        f"🧠 지능: {stats['지능']} | 🍀 운: {stats['운']}\n"
        f"🛡️ 정신력: {stats['정신력']}\n"
        f"──────────────────\n"
        f"🎒 소지품: {inventory_text}\n\n"
        f"✨ 적용 중인 아이템 효과:\n{effects_text}"
    )

    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [{
                "basicCard": {
                    "title": "📋 캐릭터 정보 및 가방",
                    "description": response_text,
                    "buttons": [{"action": "block", "label": "돌아가기", "blockId": "6a1ce5d3568d272d8eb2365b"}]
                }
            }]
        }
    })

@app.route('/reset_data', methods=['POST'])
def reset_data():
    req = request.get_json()
    user_id = get_clean_user_id(req) 
    
    if user_id in user_db:
        del user_db[user_id]
        
    response_text = (
        "🧼 [데이터 초기화 완료]\n\n"
        "당신의 모든 기억과 가방, 스탯이 깔끔하게 삭제되었습니다.\n"
        "아래 버튼을 눌러 처음부터 새롭게 캐릭터를 선택해 주세요."
    )

    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": response_text}}],
            "quickReplies": [
                {
                    "action": "block", 
                    "label": "🎭 직업 다시 선택하기", 
                    "blockId": "6a26283f95b9c60df67a5932" 
                }
            ]
        }
    })

# ==========================================
# 🛑 [신규 추가된 부분] 유물 조건부 통과 로직
# ==========================================
@app.route('/use_artifact', methods=['POST'])
def use_artifact():
    req = request.get_json()
    user_id = get_clean_user_id(req) 
    
    if user_id not in user_db:
        return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": "⚠️ 아직 게임을 시작하지 않았습니다."}}]}})
        
    player = user_db[user_id]
    client_extra = req['action'].get('clientExtra', {})
    
    # 빌더에서 전달받을 성공/실패 시 이동할 블록 ID
    success_block = client_extra.get('6a380f57f6db5c75e814cac0')
    fail_block = client_extra.get('6a1ce65fa473984e62868ba0')

    # 인벤토리에 "유물"이 있는지 검사
    if "유물" in player["inventory"]:
        title = "✨ 유물 사용!"
        desc = "가방 안의 [유물]이 강하게 빛나며 굳게 닫힌 결계를 뚫어냅니다!\n이제 안으로 들어갈 수 있습니다."
        button_label = "🔥 히든 엔딩으로"
        next_block = success_block
    else:
        title = "🔒 굳게 닫힌 문..."
        desc = "결계가 쳐져 있어 일반적인 방법으로는 지나갈 수 없습니다.\n무언가 특별한 유물이 필요할 것 같습니다."
        button_label = "돌아가기"
        next_block = fail_block

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
