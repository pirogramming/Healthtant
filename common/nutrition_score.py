from foods.models import Food

#---------------------------------------여기부터 내부적으로만 사용하는 메소드! 다른 앱에서 직접 호출할 일은 없음!--------------------------
# 나트륨(mg)을 받아 소금(g)으로 변환하는 함수
def sodium_into_salt(sodium):
    return sodium*2.5/1000

#100kcal에 함유된 nutrient의 양을 반환하는 함수
def get_100kcal_nutrient(food, nutrient):
    calorie = getattr(food, "calorie")
    #제로 음식인 경우
    if calorie == 0 or calorie == None:
        return 0
    
    nutirent_100kcal = getattr(food, nutrient, 0)/calorie * 100
    return nutirent_100kcal

def NRFgoodNutrient(nutrient, require):
    return min(100, nutrient/require*100)

def NRFbadNutrient(nutrient, require):
    return nutrient/require * 100

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
        sugar = getattr(food, "sugar", 0)
        if sugar <= cutoff[category]["sugar"][0]: return {"level": "낮음", "class": "GOOD"}
        elif sugar <= cutoff[category]["sugar"][1]: return {"level": "적정", "class": "NEUTRAL"}
        else: return {"level": "높음", "class": "BAD"}
    
    if nutrient == "saturated_fatty_acids":
        saturated_fatty_acids = getattr(food, "saturated_fatty_acids", 0)
        if saturated_fatty_acids <= cutoff[category]["saturated_fatty_acids"][0]: return {"level": "낮음", "class": "GOOD"}
        elif saturated_fatty_acids <= cutoff[category]["saturated_fatty_acids"][1]: return {"level": "적정", "class": "NEUTRAL"}
        else: return {"level": "높음", "class": "BAD"}
    
    if nutrient == "salt":
        salt = sodium_into_salt(getattr(food, "salt", 0))
        if salt <= cutoff[category]["salt"][0]: return {"level": "낮음", "class": "GOOD"}
        elif salt <= cutoff[category]["salt"][1]: return {"level": "적정", "class": "NEUTRAL"}
        else: return {"level": "높음", "class": "BAD"}

    #단백질은 음료와 고형식 기준이 동일함
    if nutrient == "protein":
        protein = getattr(food, "protein", 0)
        calorie = getattr(food, "calorie", 1)
        ratio = protein*4/getattr(food, "calorie") * 100
        if ratio < 12: return {"level": "낮음", "class": "BAD"}
        elif ratio < 20: return {"level": "적정", "class": "NEUTRAL"}
        else: return {"level": "높음", "class": "GOOD"}

    return {"level": "판정불가", "class": None}


# food의 NRF 지수를 계산하는 함수
def NRF(food):
    protein_score = NRFgoodNutrient(get_100kcal_nutrient(food, "protein"), 55)
    dietary_fiber_score = NRFgoodNutrient(get_100kcal_nutrient(food, "dietary_fiber"), 25)
    vitaminA_score = NRFgoodNutrient(get_100kcal_nutrient(food, "VitaminA"), 700)
    vitaminC_score = NRFgoodNutrient(get_100kcal_nutrient(food, "VitaminC"), 100)
    vitaminE_score = NRFgoodNutrient(get_100kcal_nutrient(food, "VitaminE"), 11)
    calcium_score = NRFgoodNutrient(get_100kcal_nutrient(food, "calcium"), 700)
    iron_content_score = NRFgoodNutrient(get_100kcal_nutrient(food, "iron_content"), 12)
    potassium_score = NRFgoodNutrient(get_100kcal_nutrient(food, "potassium"), 3500)
    magnesium_score = NRFgoodNutrient(get_100kcal_nutrient(food, "magnesium"), 315)

    saturated_fatty_acids_score = NRFbadNutrient(get_100kcal_nutrient(food, "saturated_fatty_acids"), 15)
    sugar_score = NRFbadNutrient(get_100kcal_nutrient(food, "sugar"), 100)
    salt_score = NRFbadNutrient(get_100kcal_nutrient(food, "salt"), 2000)

    good_score_sum = (protein_score + dietary_fiber_score + vitaminA_score + vitaminC_score + vitaminE_score + calcium_score + potassium_score + iron_content_score + magnesium_score)/9
    bad_score_sum = (saturated_fatty_acids_score + sugar_score + salt_score)/3

    return good_score_sum - bad_score_sum

def NutritionalScore(food):
    NRFscore = NRF(food)
    if NRFscore >= 60:
        return "A"
    elif NRFscore >= 40:
        return "B"
    elif NRFscore >= 20:
        return "C"
    elif NRFscore >= 0:
        return "D"
    else:
        return "E"