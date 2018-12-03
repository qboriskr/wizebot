from wize_bot.aphorism.aphorism import  APHORISMS, DATA_PATH, MODEL_NAME

if __name__ == '__main__':
    # APHORISMS.prepare(DATA_PATH, MODEL_NAME)
    APHORISMS.load(DATA_PATH, MODEL_NAME)
    print(APHORISMS.get_stats())
    print('================ хотим рандомность =============')
    print(APHORISMS.get_random())

    kwords = ['логика']
    print('=================== логика =====================')
    print(APHORISMS.get_fuzzy(kwords, 10))

    print('=============== хотим тупа поржать =============')
    kwords = 'твен'
    for a in APHORISMS.get_fuzzy(kwords, 30):
        print(a)

    print('============== хотим постмодернизма ============')
    kwords = 'Делез'
    for a in APHORISMS.get_fuzzy(kwords, 20):
        print(a)

    print('================ китайская мудрость ============')
    kwords = 'цзы'
    for a in APHORISMS.get_fuzzy(kwords, 20):
        print(a)
