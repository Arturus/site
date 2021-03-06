+++
title = "Как добавить колонку к pd.DataFrame"
subtitle = "...и остаться в живых"
date = 2018-10-20T00:00:00
tags=['Pandas', 'Python']
categories=['Performance', 'Programming']
summary = "...и остаться в живых? В Pandas существует по меньшей мере три официальных способа добавить колонку, не включая экзотических. Способ №1:"
# Optional featured image (relative to `static/img/` folder).
[header]
image = ""
caption = ""

+++
## Введение
В Pandas существует по меньшей мере три официальных способа добавить колонку,
не включая экзотических:

__Способ №1__
```python
import pandas as pd
df = pd.DataFrame(...)

df['column'] = value
``` 
У этого способа самый простой и очевидный синтаксис, поэтому по умолчанию
обычно используют именно его. Но наверняка каждый, кто работал
с Pandas, получал хотя бы раз в жизни такой неприятный warning при добавлении
колонки:
```diff
SettingWithCopyWarning: 
A value is trying to be set on a copy of a slice from a DataFrame.
Try using .loc[row_indexer,col_indexer] = value instead
```
Этот warning говорит нам, что существует второй способ.

__Способ №2__
```python
df.loc[:, 'column'] = value
```
Откуда же берется warning в первом способе? Он возникает, когда выполняется
несколько выборок идущих друг за другом, причем на вход следующей выборки
подаются результаты предыдущей выборки. В терминологии Pandas это называется
 *chained indexing* и выглядит например так:
```python
# Выборка по строкам, потом по колонкам
df[df['a'] > 5][['b', 'c']]

# Выборка по колонкам, потом по строкам
df[['b', 'c']][df['a'] > 5]
```
Если попытаться модифицировать результаты *chained indexing* (добавление колонки это тоже
модификация), то Pandas не поймет, что мы хотим - добавить колонку в результаты
выборки, или добавить колонку в исходный фрейм? Оба примера, приведенные ниже, эквивалентны
с точки зрения Pandas:
```python
# Добавить колонку 'b' к исходному фрейму?
df[df['a'] > 5]['b'] = 42 

# Или к результатам выборки?
df1 = df[df['a'] > 5]
df1['b'] = 42
```
Чтобы выдать `SettingWithCopyWarning`, Pandas запоминает источник данных для каждого
фрейма, 'родительский' фрейм. Если такой источник существует, т.е. фрейм является
подмножеством данных родительского фрейма, то в момент модификации выдается warning.

Второй способ позволяет нам более явным образом сообщить о своих намерениях, т.к. даёт 
совместить выборку и присваивание в одном выражении.
   
Более подробно о премудростях *chained indexing* можно прочитать в
 [документации Pandas](https://pandas.pydata.org/pandas-docs/stable/indexing.html#indexing-view-versus-copy) или
в отличной [статье на Medium](https://medium.com/dunder-data/selecting-subsets-of-data-in-pandas-part-4-c4216f84d388).   
 

__Способ №3__
```python
result = df.assign(column=value)
```
Третий способ не модифицирует исходный фрейм, что в зависимости от 
ситуации может быть как плюсом (например при повторном выполнении ячейки
в Ipython Notebook), так и минусом, загромождая код присваиваниями.
 Кроме того, при
выполнении `assign()` всегда происходит создание нового фрейма,
 что теоретически должно быть немного медленнее, чем предыдущие in-place способы.

Наличие нескольких способов сделать одну и ту же простую задачу противоречит
известному принципу [Zen of Python](https://www.python.org/dev/peps/pep-0020/) :

> There should be one—and preferably only one—obvious way to do it.

И как оказалось, проблема здесь не только в нарушении философского принципа.

## Проблема
<img src="meme.jpeg#floatright" width="350" height="197"/>
Я давно замечал, что при активном добавлении колонок во фреймы код
начинает работать подозрительно медленно. Под активным я имею в виду
сотни и тысячи добавлений - такие задачи встречаются, когда данные 
надо разбить на много мелких групп и работать с каждой отдельно.
Использование третьего способа, через `assign()` обычно ускоряло такой код,
хотя теоретически он должен работать медленнее двух первых -
 я списывал это на то, что мне
просто показалось, и никогда не делал точных замеров.

Но на последней задаче эта проблема проявилась особенно остро. Скрипт, 
который должен был пропустить через себя примерно 100Gb данных, и 
довольно бодро стартовавший с прогнозом времени выполнения 3 часа,
 был оставлен на ночь. К утру скрипт не выполнил и 20% работы и почти
  завис, потребляя при этом 100% CPU. В чём же дело?

Запуск скрипта под cProfile выявил занятную картину: основную часть времени
процесс находится внутри метода `gc.collect()`, при том, что я нигде не вызываю
сборщик мусора. Такое поведение было бы объяснимым для виртуальной
машины Java, работающей в условиях нехватки памяти, тогда бы сборщик мусора
активировался на каждый чих. Но Python?

Пришлось поглубже залезть в трассировку вызовов... и следы привели
к коду, добавляющему колонки в dataframe! Вот фрагмент кода метода
 `DataFrame._check_setitem_copy()`, занимающегося проверкой при добавлении колонки,
 и выдающего тот самый `SettingWithCopyWarning`, о котором говорилось выше :
```python
if force or self._is_copy:
    value = config.get_option('mode.chained_assignment')
    if value is None:
        return
    # see if the copy is not actually referred; if so, then dissolve
    # the copy weakref
    try:
        gc.collect(2)
        if not gc.get_referents(self._is_copy()):
            self._is_copy = None
            return
    except Exception:
        pass
```
В поле `self._is_copy` хранится weak reference на объект, являющийся
'родителем' текущего фрейма. Чтобы проверить, жив ли еще родитель,
авторы Pandas не нашли лучшего способа, чем просто запустить сборку
 мусора во всей виртуальной машине :worried:

На тестах, когда в памяти не очень много объектов,
 сборка мусора отрабатывает практически мгновенно и код не
  вызывает никаких нареканий.
 В моём же случае в памяти было закешировано около 10Gb данных, и сборщику
 мусора приходилось изрядно потрудиться, обходя все эти объекты при каждом
 добавлении колонки во фрейм.
     
## Решение
Решение было простым - раз блок кода со сборкой мусора исполняется только
при наличии 'родителя', надо сделать так, чтобы родителя не было. Я просто
добавил вызов `copy()` перед тем местом, где добавляется колонка. После
`copy()` фрейм считается 'заново рождённым', и не содержит ссылок на
источник данных:
```python
df = df.copy()
df['column'] = value
```
Скрипт сразу заработал намного быстрее, и завершился всего за час :tada:

Отмечу,
что тормоза были одинаковыми при использовании и первого и второго способа добавления
колонки, что неудивительно, т.к. оба они вызывают эту проверку.
А что же третий способ, `assign()`? Посмотрим на его код, он очень
 простой (привожу только ветку для Python 3.6):
```python
def assign(self, **kwargs):
  data = self.copy()
  for k, v in kwargs.items():
      data[k] = com._apply_if_callable(v, data)
  return data
```
Как видно, этот код делает ровно то, что я сделал вручную, ускоряя
свой скрипт: сначала копирует фрейм, а потом добавляет в него
колонки _дедовским способом_. Именно поэтому использование `assign()`,
вопреки логике, всегда ускоряло работу. 

## Выводы
Для пользователей Pandas вывод простой: надёжнее всего использовать 
`assign()`, и со стороны performance, и со стороны того, что он 
ограждает пользователя от side effects, связанных с необратимым 
изменением фрейма.
Автор [статьи](https://medium.com/dunder-data/selecting-subsets-of-data-in-pandas-part-4-c4216f84d388),
которую я рекомендовал выше, приходит к тем же 
выводам. Всегда, когда надо присвоить что-то фрейму, перед присваиванием
лучше вызвать `df.copy()`, чтобы избежать неоднозначностей. И, как показывает
мой пример, еще и получить прибавку к скорости!  

А разработчикам Pandas хорошо бы или найти способ отказаться от
 такой brute-force проверки, или хотя бы отразить её наличие в документации. 
  

  


