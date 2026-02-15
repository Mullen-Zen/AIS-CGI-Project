"""
Util functions for formatting, mapping names, and helper logic
"""

# The first two digits of the CIP code represent a broad family of studies
CIP_FAMILY_MAP = {
    "01": "Agriculture & Veterinary Sciences",
    "03": "Natural Resources & Conservation",
    "04": "Architecture & Related Services",
    "05": "Area, Ethnic, Cultural, Gender Studies",
    "09": "Communication & Journalism",
    "10": "Communications Technologies",
    "11": "Computer & Information Sciences",
    "12": "Personal & Culinary Services",
    "13": "Education",
    "14": "Engineering",
    "15": "Engineering Technologies",
    "16": "Foreign Languages & Literatures",
    "19": "Family & Consumer Sciences",
    "22": "Legal Professions & Studies",
    "23": "English Language & Literature",
    "24": "Liberal Arts & Sciences",
    "25": "Library Science",
    "26": "Biological & Biomedical Sciences",
    "27": "Mathematics & Statistics",
    "29": "Military Technologies",
    "30": "Multi/Interdisciplinary Studies",
    "31": "Parks, Recreation, Leisure, Fitness",
    "38": "Philosophy & Religious Studies",
    "39": "Theology & Religious Vocations",
    "40": "Physical Sciences",
    "41": "Science Technologies",
    "42": "Psychology",
    "43": "Homeland Security, Law Enforcement",
    "44": "Public Administration & Social Service",
    "45": "Social Sciences",
    "46": "Construction Trades",
    "47": "Mechanic & Repair Technologies",
    "48": "Precision Production",
    "49": "Transportation & Materials Moving",
    "50": "Visual & Performing Arts",
    "51": "Health Professions",
    "52": "Business, Management, Marketing",
    "54": "History"
}

"""
Returns the family name for a given CIP code
"""
def get_cip_family(cip_code):
    if not cip_code or len(str(cip_code)) < 2:
        return "Unknown CIP Family"
    
    family_code = str(cip_code).split('.')[0]
    if len(family_code) < 2:
        family_code = "0" + family_code

    return CIP_FAMILY_MAP.get(family_code, "Other/Specialized Fields")

"""
Formats a number as USD
"""
def format_currency(value):
    try:
        return f"${float(value):,.0f}"
    except (ValueError, TypeError):
        return "0"

"""
Formats a number with comma separators
"""    
def format_number(value):
    try:
        return f"{float(value):,.0f}"
    except (ValueError, TypeError):
        return "0"
    
"""
Returns a color code corresponding to a given saturation level
"""
def get_saturation_color(value):
    if value is None or value != value:
        return "off" # grey
        
    # red
    if value > 1.2:
        return "inverse" 
        
    # green
    if value < 0.8:
        return "normal"
        
    return "off"

"""
Returns a test blurb on market sentiment for a given saturation level
"""
def get_sentiment_blurb(saturation_index, job_growth_rate):
    if saturation_index > 1.2:
        return "Oversaturated markets indicate high competition and barriers to entry for even entry-level positions."
    elif saturation_index < 0.8:
        return "Undersaturated markets indicate higher compensation and better opportunity for new graduates."
    elif job_growth_rate > 0.05:
        return "This market is nearly saturated, but growing steadily. Opportunities are available, especially if you have a strong profile or relevant experience."
    elif saturation_index != 0 and saturation_index == saturation_index: # check for non-zero and non-NaN
        return "This market is saturated and not notably expanding. Opportunities may be limited, especially for new graduates without experience."
    

# if __name__ == "__main__":
#     # Quick Test
#     print(f"Family for 11.0101: {get_cip_family('11.0101')}")
#     print(f"Family for 52.0201: {get_cip_family('52.0201')}")
#     print(f"Formatted Salary: {format_currency(85000)}")