WELCOME_MSG_TEMPLATE = ""

"""
If any message is received check for active session in cache if there is then send message with button to ask to cancel the session for booking

Send interactive message with 
range 0-9, 10-19, 20-29, 30-39, 40-49, 50-59, 60-69, 70-79, 80-89,
range 0,1,2,3,4,5,6,7,8,9

else 
range 1-100, 101-200, 201-300, 301-400, 401-500, 501-600, 601-700, 701-800, 801-900, 901-1000
range 101-110, 111-120, 121-130, 131-140, 141-150, 151-160, 161-170, 171-180, 181-190, 191-200


adult_male ==== booking_adult_male_value_{}, booking_adult_male_range_{}-{}
adult_female ==== booking_adult_male_value_{}, booking_adult_male_range_{}-{}
adult_child ==== booking_adult_male_value_{}, booking_adult_male_range_{}-{}

For infant there will be only one range 
adult_infant ====booking_infant_value_{}, booking_infant_range_{}-{}
"""
