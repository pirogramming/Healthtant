from foods.models import Food

#---------------------------------------여기부터 내부적으로만 사용하는 메소드! 다른 앱에서 직접 호출할 일은 없음!--------------------------
# 나트륨(mg)을 받아 소금(g)으로 변환하는 함수
def sodium_into_salt(sodium):
    return sodium*2.5/1000

# food가 nutrient를 얼마나 가지고 있는지 가져오는 함수
def getNutrient(food, nutrient):
    return getattr(food, nutrient, 0) or 0

#----------------------------------------여기부터 직접 사용하면 되는 메소드!-------------------------------------------------------------
#영양소 이름과 food를 입력하면 영양소 함량이 GOOD, NEUTRAL, BAD 인지, 그리고 낮음/적정/높음 인지 반환하는 함수
# *주의* 영양적인 관점에서 칼로리는 낮고 높은 기준을 명시하지 않는게 좋음!! 칼로리가 낮다고 좋은 음식인게 아니고 칼로리가 높다고 안 좋은 음식인게 아니기 때문!
# 따라서 칼로리에 대한 GOOD, BAD 문구는 출력하지 않는걸로 합시다!
def get_level(nutrient, food):

    #고형식과 음료의 FSA Front-of-Pack 기준이 다르기 때문에 cutoff를 분리해서 구현 
    cutoff = {
        "drink": {"sugar":[2.5, 11.25], "saturated_fatty_acids": [0.75, 1.5], "salt": [0.3, 0.75]},
        "solid": {"sugar":[5.0, 22.5], "saturated_fatty_acids": [1.5, 5.0], "salt": [0.3, 1.5]}
        }
    
    category = "drink" if getattr(food, "food_category") == "음료류" else "solid"

    if nutrient == "sugar":
        sugar = getNutrient(food, "sugar")
        if sugar <= cutoff[category]["sugar"][0]: return {"level": "낮음", "class": "GOOD"}
        elif sugar <= cutoff[category]["sugar"][1]: return {"level": "적정", "class": "NEUTRAL"}
        else: return {"level": "높음", "class": "BAD"}
    
    if nutrient == "saturated_fatty_acids":
        saturated_fatty_acids = getNutrient(food, "saturated_fatty_acids")
        if saturated_fatty_acids <= cutoff[category]["saturated_fatty_acids"][0]: return {"level": "낮음", "class": "GOOD"}
        elif saturated_fatty_acids <= cutoff[category]["saturated_fatty_acids"][1]: return {"level": "적정", "class": "NEUTRAL"}
        else: return {"level": "높음", "class": "BAD"}
    
    if nutrient == "salt":
        salt = sodium_into_salt(getNutrient(food, "salt"))
        if salt <= cutoff[category]["salt"][0]: return {"level": "낮음", "class": "GOOD"}
        elif salt <= cutoff[category]["salt"][1]: return {"level": "적정", "class": "NEUTRAL"}
        else: return {"level": "높음", "class": "BAD"}

    #단백질은 음료와 고형식 기준이 동일함
    if nutrient == "protein":
        protein = getNutrient(food, "protein")
        calorie = getNutrient(food, "calorie")
        if calorie == 0: calorie = 1 #제로 음식인 경우 calorie로 나눠줘야 하므로 1로 처리
        ratio = protein*4/getattr(food, "calorie") * 100
        if ratio < 12: return {"level": "낮음", "class": "BAD"}
        elif ratio < 20: return {"level": "적정", "class": "NEUTRAL"}
        else: return {"level": "높음", "class": "GOOD"}

    return {"level": "판정불가", "class": None}

# 식품의 영양점수를 계산하는 함수 (0점 ~ 26점)
def NutritionalScore(food):

    score = 0

    calorie = getNutrient(food, "calorie")

    # 제로 음식인 경우 영양가치는 0임
    if calorie == 0:
        return 0
    
    carbohydrate = getNutrient(food, "carbohydrate")
    protein = getNutrient(food, "protein")
    fat = getNutrient(food, "fat")
    sugar = getNutrient(food, "sugar")
    saturated_fatty_acids = getNutrient(food, "saturated_fatty_acids")
    trans_fatty_acids = getNutrient(food, "trans_fatty_acids")
    dietary_fiber = getNutrient(food, "dietary_fiber")
    salt = getNutrient(food, "salt")

    carbohydrate_percent = carbohydrate/calorie*4*100
    protein_percent = protein/calorie*4*100
    fat_percent = fat/calorie*9*100
    sugar_percent = sugar/calorie*4*100
    saturated_fatty_acids_percent = saturated_fatty_acids/calorie*9*100
    trans_fatty_acids_percent = trans_fatty_acids/calorie*9*100

    #1. 총 열량 대비 탄수화물 비율이 적절한가?
    # 전혀 그렇지 않다 (0점) 그렇지 않다 (1점) 그렇다 (2점)
    if 55 <= carbohydrate_percent and carbohydrate_percent <= 65: score += 2 #탄수화물 비율이 55~65% 인 경우 2점
    elif 50 <= carbohydrate_percent and carbohydrate_percent <= 75: score += 1 #탄수화물 비율이 50~55% 또는 65~75%인 경우 1점
    # 이외의 구간 0점

    #2. 총 열량 대비 단백질 비율이 적절한가?
    # 전혀 그렇지 않다 (0점) 그렇지 않다 (1점) 그렇다 (2점)
    if 7 <= protein_percent and protein_percent <= 20: score += 2 # 단백질 비율이 7~20% 인 경우 2점
    elif 5 <= protein_percent and protein_percent <= 40: score += 1 # 단백질 비율이 5~7% 또는 20~40%인 경우 1점
    # 이외의 구간 0점

    #3. 총 열량 대비 지방 비율이 적절한가?
    # 전혀 그렇지 않다 (0점) 그렇지 않다 (1점) 그렇다 (2점)
    if 15 <= fat_percent and fat_percent <= 30: score += 2 #지방 비율이 15~30% 인 경우 2점
    elif 10 <= fat_percent and fat_percent <= 35: score += 1 #지방 비율이 10~15% 또는 30~35% 인 경우 1점
    # 이외의 구간 0점

    #4. 총 열량 대비 당류 비율이 적절한가?
    # 전혀 그렇지 않다 (0점) 그렇지 않다 (1점) 그렇다 (2점)
    if sugar_percent <= 10: score += 2 # 총당류 비율이 10% 이하인 경우 2점
    elif sugar_percent <= 20: score += 1 # 총당류 비율이 20% 이하인 경우 1점
    #이외의 구간 0점

    #5. 총 열량 대비 포화지방 비율이 적절한가?
    # 전혀 그렇지 않다 (0점) 그렇지 않다 (1점) 그렇다 (2점)
    if saturated_fatty_acids_percent <= 7: score += 2 # 포화지방 비율이 7% 이하인 경우 2점
    elif saturated_fatty_acids_percent <= 9: score += 1 # 포화지방 비율이 9% 이하인 경우 1점
    #이외의 구간 0점

    # 6. 총 열량 대비 트랜스지방 비율이 적절한가?
    if trans_fatty_acids == 0: score += 2 # 트랜스지방이 0%인 경우 2점
    elif trans_fatty_acids_percent <= 1: score += 1 #트랜스지방이 1% 이하인 경우 1점
    #이외의 구간 0점


    #여기부터 영양소의 절대량을 가지고 평가

    # 1회 음식 섭취 시 섭취하게 되는 영양소 함량
    serving_size = getattr(food, "serving_size", getattr(food, "weight", 100)) or 100 #1회 섭취참고량이 없다면 식품 중량을 기준으로, 식품 중량도 없다면 100g(ml)를 섭취하는 것으로 계산함
    serving_carbohydrate = carbohydrate/100*serving_size
    serving_protein = protein/100*serving_size
    serving_fat = fat/100*serving_size
    serving_sugar = sugar/100*serving_size
    serving_saturated_fatty_acids = saturated_fatty_acids/100*serving_size
    serving_dietary_fiber = dietary_fiber/100*serving_size
    serving_salt = salt/100*serving_size

    # 7. 탄수화물의 절대 함량이 적절한가?
    if 70 <= serving_carbohydrate and serving_carbohydrate <= 110: score += 2
    elif 50 <= serving_carbohydrate and serving_carbohydrate <= 120: score += 1

    # 8. 단백질의 절대 함량이 적절한가?
    if 16 <= serving_protein and serving_protein <= 36: score += 2
    elif 10 <= serving_protein and serving_protein <= 40: score += 1
    
    # 9. 지방의 절대 함량이 적절한가?
    if 16 <= serving_fat and serving_fat <= 26: score += 2
    elif 10 <= serving_fat and serving_fat <= 30: score += 1

    # 10. 포화지방의 절대 함량이 적절한가?
    if serving_saturated_fatty_acids <= 5: score += 2
    elif serving_salt <= 6.3: score += 1

    # 11. 총당류의 절대 함량이 적절한가?
    if serving_sugar <= 16: score += 2
    elif serving_sugar <= 20: score += 1

    # 12. 식이섬유의 절대 함량이 적절한가?
    if 8.3 <= serving_dietary_fiber and serving_dietary_fiber <= 11.6: score += 2
    elif 6.6 <= serving_dietary_fiber and serving_dietary_fiber <= 11.6: score += 1

    # 13. 나트륨의 절대 함량이 적절한가?
    if serving_salt <= 600: score += 2
    elif serving_salt <= 700: score += 1

    return score

# 식품의 영양점수를 기반으로 레터그레이드를 반환하는 함수 (A~E)
def letterGrade(food):
    score = NutritionalScore(food)
    if score <= 5:
        return "E"
    elif score <= 10:
        return "D"
    elif score <= 15:
        return "C"
    elif score <= 20:
        return "B"
    else:
        return "A"