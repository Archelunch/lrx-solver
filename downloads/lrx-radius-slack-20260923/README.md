# LRX: контрпример к абсолютному радиусу проекции

23 сентября 2026. Начните с reports/cycle6/RESULTS.md.

При m=8,r=3 и v=(2,1,0,0,0,7,8,6,5,4,3): P=42, d(v)=47,
A_42(v)=49>48. Кандидат A_P<=P+m-2 опровергнут точным конечным
расчётом двух независимых алгоритмов. Основная гипотеза НЕ опровергнута.

Воспроизведение из этой папки:

    python3 experiments/cycle6/reproduce.py
    python3 experiments/cycle6/reproduce.py --full
    python3 experiments/cycle6/reproduce.py --extended

Первый режим: stdlib Python, малые графы и replay слов.
--full: полный нижний сертификат контрпримера; требуется clang++ или g++ C++17.
--extended: также соседние размеры. Запуски создают новые файлы.

План: research/cycle6/PROJECT.md.
Рецензия: research/cycle6/cloud-proof/REVIEW_FINAL.md.
Уточнение версии исходников: reports/cycle6/SOURCE_VERSION_NOTE.md.
Следующий проход: reports/cycle6/NEXT_PASS.md.
Реестр утверждений: reports/cycle6/claims.json.
Целостность: MANIFEST.json. Проверка: python3 verify_bundle.py

Отчёт подготовлен ИИ; человеческая рецензия пока не выполнена.
Lean-файлы проверяют только вспомогательные/условные леммы,
не полное перечисление графов и не общую гипотезу.
