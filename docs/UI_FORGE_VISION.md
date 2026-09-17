# UI Forge — проектная концепция

**Статус:** идея зафиксирована; первый рабочий прототип развивается внутри Courier Control.

## 1. Что это

UI Forge — универсальный контур разработки и контроля фронтенда, который можно подключать к разным проектам.

Цель: заменить цикл «изменить CSS → выложить в production → искать дефект на телефоне → исправлять» на управляемый процесс:

**Design → Components → Automated UI Tests → Visual Regression → Staging → Human Review → Production → Checkpoint.**

Production никогда не используется как среда разработки.

## 2. Что получает разработчик

UI Forge должен давать проекту:

- единые design tokens: размеры, отступы, радиусы, контролы и типографика;
- UI Preview — страницу-витрину компонентов и состояний;
- Playwright-проверки Chromium/WebKit;
- набор стандартных viewport: 320, 375, 390/393, 430, 768, 1440;
- автоматическое обнаружение page overflow и выхода контролов за viewport;
- проверки ключевых пользовательских экранов и форм;
- visual regression: BEFORE / AFTER / DIFF;
- изолированный staging;
- human approval первого visual baseline и значимых изменений;
- CI gate перед попаданием интерфейсных изменений в stable/main;
- checkpoint после подтверждённого production-релиза.

## 3. Главный пользовательский сценарий

1. Изменение создаётся в feature-ветке.
2. UI Forge запускает source/UI-contract tests.
3. Браузерные тесты открывают критические страницы на заданных viewport и браузерах.
4. Геометрические проверки ищут overflow, выходы элементов и другие детерминированные дефекты.
5. Visual Regression показывает только реально изменившиеся экраны.
6. Изменение разворачивается на отдельном staging с отдельными данными/runtime.
7. Человек проверяет staging, включая реальное мобильное устройство.
8. Только одобренная версия попадает в main/production.
9. После проверки production создаётся новый checkpoint. Старый checkpoint не перемещается.

## 4. Каким должен быть отчёт

Вместо длинного технического лога пользователь должен получать короткий результат:

    UI FORGE REPORT

    ✓ 320
    ✓ 375
    ✓ iPhone / WebKit
    ✓ 430
    ✓ Tablet
    ✓ Desktop

    ✓ no page overflow
    ✓ controls inside viewport
    ✓ forms/navigation smoke tests

    Visual changes:
    Statistics      CHANGED
    Dashboard       SAME
    Courier Create  SAME
    Route Editor    SAME

    REVIEW REQUIRED: Statistics

Для изменившегося экрана показываются BEFORE / AFTER / DIFF.

## 5. Архитектурный принцип

Универсальная часть должна жить отдельно от бизнес-приложения. После обкатки прототипа Courier Control планируется выделить ядро в отдельный репозиторий, рабочее имя:

**Hardoffx/ui-forge**

Предполагаемая структура:

    ui-forge/
      tokens/
      preview/
      tests/
      viewports/
      visual-baselines/
      staging/
      github-actions/
      ui-forge.config

Конкретный проект должен описывать главным образом критические страницы, браузеры/viewports, staging и проектные design tokens. Повторяемая инфраструктура должна предоставляться UI Forge.

## 6. Первый пилот: Courier Control

Courier Control — первый реальный проект для проверки подхода.

На момент фиксации концепции в feature-ветке уже создаются:
- design tokens;
- UI contracts;
- UI Preview;
- Playwright responsive tests;
- авторизованные dispatcher tests;
- Visual Regression infrastructure;
- отдельный staging на Gunicorn 8011 и отдельной SQLite.

Production Courier Control остаётся отдельным контуром на 8010/main.

## 7. Правила, которые нельзя потерять

- GitHub — источник истины для кода.
- Feature branch → tests → staging → approval → main → production → checkpoint.
- Не утверждать автоматически первый visual baseline.
- Не обновлять baseline только ради прохождения CI: изменение сначала проверяет человек.
- Staging никогда не использует production DB/runtime.
- UI должен проверяться в WebKit/iPhone-контексте, а не только Chromium.
- Намеренный горизонтальный scroll компонента не считается page-level overflow.
- Повторяемый CSS/компоненты не должны размножаться по шаблонам.
- Система должна уменьшать ручную работу, а не добавлять церемонию.

## 8. Следующее развитие

После завершения staging-пилота Courier Control:

1. утвердить первые baselines;
2. довести отчёт BEFORE / AFTER / DIFF;
3. выделить framework-neutral ядро из Courier Control;
4. создать отдельный репозиторий ui-forge;
5. сделать подключение нового проекта максимально коротким;
6. использовать следующие реальные проекты как проверку универсальности системы.

Главный критерий успеха: разработчик занимается продуктом и принимает визуальные решения, а UI Forge автоматически выполняет повторяемую проверку качества интерфейса.
