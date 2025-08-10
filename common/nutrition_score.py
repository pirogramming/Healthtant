from foods.models import Food

# 나트륨(mg)을 받아 소금(g)으로 변환하는 함수
def sodium_into_salt(sodium):
    return sodium*2.5/1000

#영양소 이름과 food를 입력하면 영양소 함량이 GOOD, BAD 인지, 그리고 낮음/적정/높음 인지 반환하는 함수
def get_level(nutrient, food):
    if nutrient == "sugar":
        sugar = getattr(food, "sugar", 0)
        if sugar <= 5.0: return {"level": "낮음", "class": "GOOD"}
        elif sugar <= 22.5: return {"level": "적정", "class": "GOOD"}
        else: return {"level": "높음", "class": "BAD"}
    
    if nutrient == "saturated_fatty_acids":
        saturated_fatty_acids = getattr(food, "saturated_fatty_acids", 0)
        if saturated_fatty_acids <= 1.5: return {"level": "낮음", "class": "GOOD"}
        elif saturated_fatty_acids <= 5.0: return {"level": "적정", "class": "GOOD"}
        else: return {"level": "높음", "class": "BAD"}
    
    if nutrient == "salt":
        salt = sodium_into_salt(getattr(food, "salt", 0))
        if salt <= 0.3: return {"level": "낮음", "class": "GOOD"}
        elif salt <= 1.5: return {"level": "적정", "class": "GOOD"}
        else: return {"level": "높음", "class": "BAD"}

    if nutrient == "protein":
        protein = getattr(food, "protein", 0)
        ratio = protein*4/getattr(food, "calorie", 0)
        return ratio
