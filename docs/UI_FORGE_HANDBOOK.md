# UI Forge — руководство, архитектура и план развития

**Статус:** живой документ. Courier Control — первый пилот.  
**Текущий этап:** первый утверждённый visual baseline создан; 30 snapshot-проверок локально воспроизводятся. CI пилота ещё не считается зелёным: run #328 упал на Responsive browser tests, visual regression был пропущен.

## 1. Зачем существует UI Forge

UI Forge — контур разработки фронтенда, который превращает визуальную работу из ручного цикла «поправить CSS → проверить один экран → случайно сломать другой» в воспроизводимый процесс:

**Intent → Design → Shared UI → Automated Geometry → Visual Regression → Staging → Human Approval → Main → Production → Immutable Checkpoint**

Инструмент не должен заменять человека в вопросе вкуса. Его задача — автоматически ловить повторяемые ошибки, показывать человеку только значимые визуальные изменения и сохранять утверждённое состояние.

## 2. Что считать источником истины

- GitHub — источник истины для кода и утверждённых baseline.
- Feature branch — место разработки.
- Staging — место проверки кандидата, никогда не production.
- Visual baseline — утверждённый человеком визуальный контракт.
- Main — только прошедшее проверки и review состояние.
- Checkpoint — новая неизменяемая точка после подтверждения production.
- Старый checkpoint никогда не передвигается.
- Baseline никогда не перезаписывается только ради зелёного CI.

## 3. Слои системы

### 3.1 Design system
Design tokens задают общие размеры, интервалы, радиусы, типографику и поведение контролов. Повторяемые стили должны становиться общими компонентами, а не копироваться по страницам.

### 3.2 UI Preview
UI Preview — лаборатория компонентов и состояний. Здесь должны существовать normal/hover/focus/disabled/error/loading/empty/long-content состояния, чтобы изменение компонента можно было проверить отдельно от бизнес-сценария.

### 3.3 Source contracts
Быстрые тесты проверяют архитектурные правила: подключение tokens, отсутствие нежелательного inline/reusable CSS, наличие preview-маршрутов и другие дешёвые инварианты.

### 3.4 Geometry / responsive tests
Playwright открывает страницы на целевых viewport и проверяет детерминированные дефекты: page-level horizontal overflow, элементы за viewport, критические формы и навигацию. Намеренно горизонтально прокручиваемые компоненты не считаются page overflow.

### 3.5 Visual regression
Для критических страниц хранится screenshot baseline. Новый рендер сравнивается с утверждённым. При изменении система должна давать BEFORE / AFTER / DIFF и имя экрана/viewport, а не заставлять человека читать длинный лог.

### 3.6 Staging
Staging имеет отдельные приложение, runtime, БД, секреты и порт. Он нужен для реального браузера и устройства после автоматических проверок.

### 3.7 Human gate
Человек утверждает первый baseline и любые намеренные существенные изменения. Автоматика отвечает «изменилось/сломалось», но не принимает эстетическое решение.

## 4. Текущая реализация Courier Control

Playwright-проекты:
- mobile-320 — 320×700;
- mobile-375 — 375×812;
- iphone-webkit — iPhone 13 / WebKit;
- mobile-430 — 430×932;
- tablet-768 — 768×1024;
- desktop-1440 — 1440×900.

Visual targets:
- Dashboard;
- Statistics;
- Courier Create;
- Route Create;
- UI Preview.

Это даёт 5 × 6 = **30 visual snapshots**.

Тестовый runtime изолирован:
- UI_TESTING=1;
- SQLite: /tmp/courier-control-ui-tests.sqlite3;
- детерминированный тестовый пользователь создаётся только при UI_TESTING=1;
- public staging DB не должна содержать эти test credentials.

Staging:
- /opt/courier-control-staging;
- Gunicorn 127.0.0.1:8011;
- staging.routecontrol.ru;
- отдельная SQLite.

Production:
- /opt/courier-control;
- Gunicorn 127.0.0.1:8010;
- main;
- отдельная production SQLite.

## 5. Ежедневный рабочий процесс

### A. Перед изменением
Сформулировать:
1. какой экран/компонент меняется;
2. что именно должно стать лучше;
3. какие состояния затрагиваются;
4. что визуально должно остаться неизменным.

### B. Реализация
Работать только в feature branch. Сначала переиспользовать token/component; локальный CSS добавлять лишь когда это действительно свойство конкретного экрана.

### C. Быстрые проверки
Сначала дешёвые проверки Django/source contracts. Затем responsive browser tests. Только после них visual regression.

### D. Visual review
Если screenshot отличается, определить причину:
- **BUG** — исправить код, baseline не менять;
- **INTENDED** — показать изменение человеку;
- **NONDETERMINISM** — стабилизировать тест/данные/шрифты/анимацию, baseline не менять.

Только для INTENDED + APPROVED разрешено обновление baseline.

### E. Staging
Развернуть тот же commit на staging. Проверить реальный iPhone и ключевой пользовательский путь. Staging должен сообщать точный commit SHA.

### F. Release
После зелёного CI и human approval: merge в main → production deploy → health/smoke/browser verification → новый immutable checkpoint.

## 6. Как максимально продуктивно работать с AI/ChatGPT

В новом чате достаточно дать короткий handoff:

> Продолжаем UI Forge для Hardoffx/courier-control. Прочитай docs/UI_FORGE_VISION.md, docs/UI_FORGE_HANDBOOK.md, docs/UI_QUALITY_PIPELINE.md и docs/UI_REVIEW_CHECKLIST.md. Рабочая ветка feat/ui-quality-pipeline. Сначала проверь фактическое состояние GitHub/CI и продолжай с незавершённого шага. Не меняй main и production без завершения pipeline.

Для новой UI-задачи хороший запрос:

> Экран: <название/URL>. Цель: <что изменить>. Эталон: <скрин/описание>. Сохрани остальной интерфейс без изменений. Сделай изменение в feature branch, прогони contracts/responsive/visual tests, покажи только реальные visual diffs и подготовь staging к моей проверке. Baseline без моего утверждения не обновляй.

Для найденного бага:

> Исправь этот конкретный дефект. Сначала воспроизведи его тестом, затем сделай минимальный fix и докажи, что тест теперь проходит и соседние visual baselines не изменились.

Для продолжения после паузы:

> Сначала прочитай документацию UI Forge и проверь HEAD, git status, PR и последний CI. Не доверяй старому описанию состояния, если GitHub показывает другое.

### Что AI должен сообщать после каждого этапа
Коротко и проверяемо:
- branch + commit SHA;
- какие проверки запущены;
- сколько прошло/упало;
- какие экраны визуально изменились;
- staging SHA/health;
- что требует human approval;
- следующий единственный шаг.

Нельзя говорить «готово», пока требуемые проверки фактически не прошли.

## 7. Команды пилота

Локальный/серверный browser test runtime требует Python из venv. Текущий рабочий вариант на staging:

    cd /opt/courier-control-staging
    export PATH="/opt/courier-control-staging/.venv/bin:$PATH"
    CI=1 npx playwright test

Visual regression без изменения baseline:

    CI=1 npx playwright test tests/ui/visual.spec.js

Обновление baseline допустимо только после human approval:

    CI=1 npx playwright test tests/ui/visual.spec.js --update-snapshots

Проверка GitHub CI:

    gh pr checks 10

или:

    gh run list --branch feat/ui-quality-pipeline --limit 5

Лог упавшего run:

    gh run view <RUN_ID> --log-failed

## 8. Правила visual baseline

1. Первый baseline создаётся только после проверки человеком.
2. Baseline коммитится в Git.
3. Обычный CI только сравнивает; он не обновляет baseline.
4. Любое отличие сначала классифицируется.
5. Нельзя массово принять snapshots, не просмотрев причину изменений.
6. Baseline должен строиться на детерминированных данных.
7. Динамические дата/время, анимации, caret, случайные ID и внешние нестабильные ресурсы должны быть заморожены/исключены.
8. При изменении shared component нужно ожидать diff на всех зависимых экранах и просматривать их как группу.

## 9. Тестовые данные

Следующая ступень — перейти от «детерминированно пустых страниц» к именованным UI-сценариям:
- empty;
- normal;
- dense/long-content;
- error/problem;
- completed;
- mixed delivery statuses.

Seed должен быть идемпотентным, детерминированным и разрешённым только в UI_TESTING. Production/staging данные не используются для visual tests.

## 10. План развития UI Forge

### Phase 1 — Pilot hardening
- добиться полностью зелёного CI;
- устранить различия локальной и CI среды;
- убрать зависимость от случайного PATH для Python;
- сделать production-like test server там, где это не ухудшает воспроизводимость;
- добавить репрезентативные deterministic fixtures;
- консолидировать накопившийся CSS без visual diff;
- сформировать удобный artifact report.

### Phase 2 — Visual review UX
- автоматические BEFORE / AFTER / DIFF;
- HTML-отчёт с группировкой экран → viewport;
- summary в PR;
- ссылки только на изменившиеся изображения;
- approval manifest: кто/какой commit/baseline утвердил;
- понятные статусы SAME / CHANGED / FAILED / REVIEW REQUIRED.

### Phase 3 — Accessibility & interaction
- keyboard/focus smoke tests;
- accessibility scan;
- minimum touch targets;
- contrast checks там, где они надёжны;
- loading/error/empty states;
- navigation/back behavior;
- optional reduced-motion/dark-mode/locale matrices.

### Phase 4 — Performance
- budgets для CSS/JS/assets;
- Core Web Vitals/Lighthouse как отдельный сигнал, а не visual gate;
- обнаружение тяжёлых изображений/шрифтов;
- screenshot/test sharding и кеширование браузеров для быстрого CI.

### Phase 5 — Framework-neutral core
Выделить повторяемую часть в Hardoffx/ui-forge:
- runner;
- viewport registry;
- visual comparator;
- report generator;
- GitHub Actions templates;
- adapters для auth/seed/start-server;
- project config.

Проект должен подключаться декларативно, например:

    project: courier-control
    base_url: http://127.0.0.1:8000
    browsers: [chromium, webkit]
    viewports: [320, 375, iphone, 430, 768, 1440]
    pages:
      - name: dashboard
        path: /dispatcher/
        auth: dispatcher
      - name: statistics
        path: /dispatcher/stats/
        auth: dispatcher

Формат конфигурации ещё не является стабильным API — это направление развития.

### Phase 6 — Productized workflow
Цель: одна команда уровня:

    ui-forge verify

Она должна:
1. поднять изолированный runtime;
2. подготовить fixtures;
3. выполнить contracts;
4. выполнить responsive/interactions;
5. сравнить visual baseline;
6. собрать BEFORE/AFTER/DIFF;
7. выдать короткий machine + human readable report;
8. вернуть корректный exit code для CI.

Дополнительные команды:
- ui-forge doctor — диагностика окружения;
- ui-forge preview — component laboratory;
- ui-forge approve — контролируемое принятие просмотренного baseline;
- ui-forge report — открыть последний отчёт;
- ui-forge init — подключить новый проект.

## 11. Принципы расширяемости

Ядро не должно знать бизнес-логику Courier Control. Проект предоставляет adapters:
- startServer;
- seedData;
- authenticate(role);
- pages/scenarios;
- ignore/allow rules для geometry;
- project tokens;
- staging metadata.

Все новые проверки должны отвечать трём требованиям:
1. ловят реальный класс дефектов;
2. достаточно детерминированы для CI;
3. экономят больше ручной работы, чем создают.

Flaky-тест не является качественным gate. Его нужно стабилизировать или временно вынести из blocking pipeline с явным статусом.

## 12. Definition of Done для UI-изменения

Изменение считается завершённым только когда:
- source/contracts green;
- responsive/geometry green;
- visual regression green либо intentional diffs утверждены;
- staging содержит тот же commit;
- critical flow проверен;
- реальное целевое устройство проверено, когда изменение затрагивает mobile/native rendering;
- PR готов и понятен;
- после merge production проверен;
- создан новый checkpoint.

## 13. Текущее состояние на 2026-09-18

Утверждённый дизайн Courier Control находится в feature branch. Первый baseline содержит 30 snapshots и был дважды проверен на staging: сначала создан с --update-snapshots, затем все 30 прошли без обновления.

Baseline/test-isolation commit:

    00faa9cef898d1781d6f252f6fe4c155be3ce6be
    test(ui): approve visual baselines and isolate browser tests

Draft PR: #10.

GitHub CI run #328 для этого commit:
- Django checks/tests: PASS;
- UI source guardrails: PASS;
- Node/Playwright install: PASS;
- Responsive browser tests: FAIL;
- Visual regression: SKIPPED из-за предыдущего failure.

**Следующий шаг после чтения этого документа:** получить точный failed log run 35320886951, исправить причину Responsive browser tests минимальным изменением, локально воспроизвести, push, затем добиться запуска и прохождения visual regression. Main пока не merge.

## 14. Связанные документы

- docs/UI_FORGE_VISION.md — исходная концепция;
- docs/UI_QUALITY_PIPELINE.md — правила Courier Control pipeline;
- docs/UI_REVIEW_CHECKLIST.md — human review checklist;
- playwright.config.js — текущая browser matrix/runtime;
- tests/ui/ — executable specification.

Этот handbook должен обновляться при изменении архитектуры или рабочего процесса. Его задача — позволить продолжить разработку в новом чате, на другом компьютере или другим разработчиком без потери принципов и контекста.


---

# 15. Целевой продукт: AI-native UI Engineering Agent

## 15.1. Новое определение продукта

Долгосрочная цель UI Forge шире visual regression framework. UI Forge должен стать **AI-native средой проектирования, реализации, проверки и безопасного внедрения пользовательских интерфейсов**, где человек задаёт намерение и принимает визуальные решения, а система самостоятельно выполняет повторяемую инженерную работу.

Целевой цикл:

**Intent → Design Proposals → Human Selection → Design Contract → Autonomous Implementation Loop → Multimodal Verification → Real Staging → Human Acceptance → Release Pipeline → Production Verification → Immutable Checkpoint**

Главный UX-принцип: пользователь работает с UI Forge через естественный диалог и визуальные результаты. Playwright, browser matrix, fixtures, DOM geometry, screenshot diff, CI, staging и release orchestration остаются внутренними механизмами.

## 15.2. Основной сценарий взаимодействия

Пользователь может сказать:

> Создай четыре варианта мобильного Dashboard. Сохрани функции текущего экрана, но сделай интерфейс современнее и удобнее одной рукой.

UI Forge:
1. анализирует существующий экран, компоненты, маршруты и ограничения проекта;
2. формирует несколько визуально и структурно различающихся design proposals;
3. показывает их пользователю;
4. принимает естественно-языковые уточнения: «карточки из C, шапку из A», «кнопку сделать компактнее»;
5. повторяет design iteration до явного утверждения;
6. фиксирует выбранный вариант как versioned Design Contract;
7. создаёт feature branch/workspace;
8. реализует настоящий frontend;
9. самостоятельно выполняет цикл render → inspect → diagnose → repair → verify;
10. показывает пользователю уже настоящую staging-страницу только когда кандидат достиг достаточного качества и прошёл автоматические gates;
11. принимает финальные человеческие корректировки;
12. после явного acceptance запускает release pipeline.

Таким образом, пользователь не обязан наблюдать промежуточные неудачные реализации и не обязан вручную управлять тестовой инфраструктурой.

# 16. Design Contract

Утверждённая картинка не должна быть единственным источником требований. Screenshot не описывает интерактивность, адаптивность, допустимый scroll, состояния ошибок и смысл компонентов. Поэтому UI Forge вводит **Design Contract** — версионированное представление утверждённого намерения.

Design Contract должен содержать несколько слоёв.

## 16.1. Reference layer

- утверждённые reference images;
- optional references для нескольких viewport;
- crop/region metadata;
- допустимые visual masks;
- идентификатор design revision;
- provenance: generated / uploaded / existing-page / sketch;
- human approval metadata.

## 16.2. Structural layer

Описывает важные элементы и отношения:
- component identity;
- hierarchy;
- relative alignment;
- ordering;
- expected containment;
- minimum/maximum dimensions;
- responsive transitions;
- allowed component-level horizontal scroll;
- forbidden page-level overflow.

Пример концептуального контракта:

    Dashboard.Actions:
      layout: row
      children: [ExcelImport, AddDelivery]
      equal_height: true
      inside_viewport: true

    Dashboard.KPI:
      mobile:
        overflow: component-horizontal-scroll
      page:
        overflow_x: forbidden

## 16.3. Visual layer

- colors/tokens;
- typography;
- spacing;
- radius;
- shadows;
- icon treatment;
- component proportions;
- region-level perceptual similarity requirements.

Visual layer не должен требовать абсолютного pixel-perfect совпадения там, где браузерный рендеринг объективно отличается. Порог должен быть contextual/perceptual.

## 16.4. Semantic layer

Описывает **почему** интерфейс устроен именно так:
- primary/secondary actions;
- визуальный приоритет;
- compact/comfortable intent;
- information hierarchy;
- элементы, которые нельзя скрывать;
- допустимые компромиссы при малой ширине;
- business-critical affordances.

Это позволит агенту отличать случайный pixel drift от изменения, нарушающего продуктовый замысел.

## 16.5. Interaction layer

- click/tap outcomes;
- navigation;
- back behavior;
- keyboard/focus;
- form validation;
- disabled/loading/error/success;
- gestures/scroll;
- modal/dialog behavior.

## 16.6. Responsive layer

Design Contract должен описывать не набор независимых картинок, а правила перехода между состояниями. Система должна проверять промежуточные ширины и искать breakpoint defects, а не только заранее выбранные 320/375/430/768/1440.

# 17. Autonomous Implementation Loop

После утверждения Design Contract UI Forge запускает автономный инженерный цикл.

## 17.1. Observe

Система собирает:
- DOM snapshot;
- computed styles;
- bounding boxes;
- accessibility tree;
- screenshot;
- browser console;
- network/application errors;
- interaction traces;
- текущий source dependency graph.

## 17.2. Compare

Кандидат сравнивается одновременно с:
1. reference image;
2. structural contract;
3. semantic contract;
4. interaction contract;
5. responsive invariants;
6. предыдущими утверждёнными экранами проекта.

## 17.3. Diagnose

Вместо сообщения «screenshot differs 2.7%» система должна локализовать проблему:

    Dashboard / 375 / Actions
    AddDelivery shifted +11px Y
    Expected equal alignment with ExcelImport
    Probable source: mobile-stability.css rule ...
    Unaffected regions: Header, KPI, Navigation

Диагностика должна связывать visual region → DOM node → component → CSS/template/source ownership.

## 17.4. Repair

Агент формирует минимальный patch, ограниченный затронутой областью. После каждого patch выполняется повторная проверка. Если изменение ухудшило другие approved regions, оно откатывается или пересматривается.

## 17.5. Convergence

Цикл продолжается до одного из состояний:
- PASS — контракт выполнен;
- REVIEW_READY — оставшиеся отличия допустимы/субъективны и нужен человек;
- BLOCKED — агент не может безопасно улучшить результат;
- REGRESSION — исправление вызывает неприемлемые побочные изменения.

Система не должна бесконечно «подкручивать CSS». Нужны iteration budget, convergence criteria и rollback.

# 18. Multimodal Inspector

UI Forge должен объединять несколько независимых сигналов.

## 18.1. Pixel/perceptual vision
Определяет visual drift, геометрию крупных областей, spacing, цветовые и типографические расхождения.

## 18.2. DOM geometry
Даёт точные координаты, размеры, overflow, stacking, clipping и relationships.

## 18.3. Accessibility tree
Помогает понять роль элемента и обнаружить ситуации, когда визуально правильный control семантически сломан.

## 18.4. Interaction probes
Проверяют, что визуально правильная кнопка действительно нажимается, форма отправляется, back работает, dialog закрывается.

## 18.5. Source mapping
Связывает дефект с конкретными template/component/style declarations и dependency graph.

Ни один отдельный сигнал не считается достаточным доказательством корректности UI.

# 19. Три пользовательских режима

## 19.1. DESIGN

Запросы вида:
> Придумай новый экран.
> Покажи четыре варианта.
> Возьми шапку из A и карточки из C.

Результат — design proposals и затем утверждённый Design Contract. Production code до утверждения дизайна не требуется.

## 19.2. IMPLEMENT

Запрос:
> Этот вариант утверждаю. Реализуй.

UI Forge переводит Design Contract в production-quality frontend, самостоятельно выполняя implementation loop. Пользователь подключается снова на стадии REVIEW_READY.

## 19.3. REPAIR

Запрос:
> На iPhone уехала кнопка назад. Исправь.

Для локального дефекта отдельный design proposal не нужен. Система:
reproduce → isolate → minimal patch → regression verification → staging review.

Режим определяется автоматически, но пользователь может задать его явно.

# 20. Conversational Control Plane

Чат должен стать главным control plane UI Forge.

Пользователь говорит на уровне намерения:
- «сгенерируй варианты»;
- «вариант C»;
- «шапку возьми из A»;
- «утверждаю»;
- «реализуй»;
- «эта кнопка темнее»;
- «оставляем».

Система переводит эти команды в versioned operations.

Критически важные решения должны иметь явные состояния:
- PROPOSED;
- DESIGN_APPROVED;
- IMPLEMENTING;
- REVIEW_READY;
- UI_ACCEPTED;
- RELEASE_CANDIDATE;
- RELEASED.

Фраза пользователя «утверждаю дизайн» не равна «разрешаю production deploy». Design approval и final implementation acceptance — разные gates.

# 21. UI Graph и автоматическое исследование приложения

В зрелой версии новый проект не должен требовать ручного перечисления каждой страницы.

UI Forge строит **UI Graph**:
- reachable routes/screens;
- auth roles;
- links/navigation edges;
- forms;
- dialogs;
- reusable components;
- important states;
- user journeys.

После discovery пользователь/проект задаёт важность:

    critical:
      - login
      - dashboard
      - route-editor
    important:
      - statistics
    exclude:
      - debug

Graph используется для test generation, impact analysis и определения regression scope.

Discovery не должен бесконтрольно выполнять destructive actions. Mutating flows запускаются только в disposable/test runtime с известными fixtures.

# 22. Dependency Graph и risk-based testing

Полная browser matrix полезна перед release, но слишком дорога для каждой CSS-правки.

UI Forge должен строить связи:

**source file → token/component → rendered regions → screens → user journeys**

При изменении stats.css система сначала запускает tests для Statistics и shared dependencies. При изменении глобального token запускается более широкая матрица.

Уровни:
- FAST — source/contracts + directly affected screens;
- STANDARD — affected + dependent screens + key browsers;
- RELEASE — полная матрица и critical journeys.

Перед merge/release сокращённый FAST режим не заменяет полный RELEASE gate.

# 23. Автоматическая генерация тестов

На базе UI Graph, Design Contract и accessibility/DOM metadata UI Forge должен генерировать:
- viewport geometry assertions;
- smoke interactions;
- navigation assertions;
- visual targets;
- component state coverage;
- form validation cases;
- breakpoint probes.

Generated tests должны хранить provenance: почему тест существует и из какого contract/route/component он получен. Человек может закрепить важный generated test как permanent contract.

# 24. Deterministic Scenario Engine

Visual quality невозможно надёжно оценивать на случайных данных.

Нужен Scenario Engine с именованными состояниями:
- empty;
- normal;
- dense;
- long-content;
- error;
- loading;
- completed;
- mixed;
- role-specific.

Каждый scenario:
- versioned;
- deterministic;
- idempotent;
- isolated;
- не использует production DB;
- способен восстановить исходное состояние.

Design Contract может ссылаться на конкретный scenario, например:

    screen: dashboard
    scenario: mixed-deliveries
    viewport: mobile-375

# 25. Visual Diff Intelligence

Вместо одного общего diff система должна строить:
- BEFORE;
- AFTER;
- pixel DIFF;
- perceptual DIFF;
- DOM overlay;
- changed-region map;
- component ownership;
- likely source cause.

Diff классифицируется:
- EXPECTED;
- UNEXPECTED;
- ENVIRONMENTAL;
- NONDETERMINISTIC;
- NEEDS_HUMAN_JUDGMENT.

Система может предложить классификацию, но изменение утверждённого Design Contract без human approval запрещено.

# 26. Human Review UX

Пользователь не должен читать CI logs при нормальной работе.

Целевой review:

    Dashboard v3.1 — REVIEW READY

    ✓ Structure
    ✓ Responsive
    ✓ Interactions
    ✓ Accessibility
    ✓ Visual consistency

    Remaining intentional changes: 2

    [REFERENCE] [REAL] [DIFF]

    Open real staging page

    Actions:
    - Accept implementation
    - Request changes
    - Compare variants

При request changes естественно-языковая обратная связь становится новой design revision или implementation constraint.

# 27. Release Orchestrator

После **final UI acceptance**, а не после design selection, запускается release candidate pipeline:

1. freeze implementation SHA;
2. full deterministic test reset;
3. source/security/contracts;
4. full browser matrix;
5. full visual regression;
6. critical interaction journeys;
7. build/package checks;
8. PR status verification;
9. merge according to project policy;
10. production deploy;
11. health check;
12. production smoke verification;
13. optional production visual sanity check без использования production data для baseline;
14. immutable checkpoint;
15. release report.

Любое падение останавливает progression. Автоматический rollback может стать отдельной capability, но должен быть проектно настроен и проверяем.

# 28. Safety model для автономного агента

Автономность должна быть высокой внутри безопасного sandbox, но границы окружений должны быть жёсткими.

- DESIGN sandbox: свободные эксперименты.
- TEST runtime: disposable data, автоматические mutations разрешены.
- STAGING: deployment разрешён pipeline-политикой проекта.
- MAIN/PRODUCTION: только после соответствующих gates.
- Production data никогда не используется как fixture.
- Credentials не попадают в screenshots/artifacts/logs.
- Destructive UI discovery запрещён вне disposable environment.
- Каждый autonomous patch имеет commit/diff/trace.
- Каждый automatic rollback проверяем.
- Human approval имеет audit record.

# 29. Техническая архитектура будущего standalone UI Forge

Предполагаемые подсистемы:

    ui-forge/
      core/
        orchestrator
        state-machine
        policy-engine
        project-model
      design/
        proposal-engine
        contract-schema
        reference-store
      discovery/
        ui-graph
        route-crawler
        component-map
      runtime/
        environment-adapters
        scenario-engine
        auth-adapters
      browsers/
        playwright-runner
        viewport-registry
        interaction-probes
      inspect/
        visual-inspector
        dom-geometry
        accessibility
        source-mapper
      repair/
        diagnosis
        patch-planner
        convergence-controller
        rollback
      regression/
        baseline-store
        diff-engine
        impact-analysis
      review/
        report-generator
        before-after-diff
        approval-manifest
      release/
        ci-adapter
        staging-adapter
        release-orchestrator
        checkpoint-manager
      adapters/
        django
        react
        vue
        generic-web
      cli/
      api/

Framework adapters не должны менять core semantics.

# 30. Состояние и артефакты

Для воспроизводимости UI Forge должен сохранять machine-readable artifacts:
- project manifest;
- Design Contract;
- UI Graph;
- scenario manifest;
- baseline manifest;
- approval manifest;
- run manifest;
- diff report;
- release manifest.

Каждый run связывается с:
- repository;
- branch;
- commit SHA;
- tool version;
- browser versions;
- scenario version;
- contract version;
- environment fingerprint.

Это позволит объяснить, **почему** конкретный UI был принят и при каких условиях он проверялся.

# 31. CLI и API

Целевой CLI:

    ui-forge init
    ui-forge doctor
    ui-forge discover
    ui-forge design
    ui-forge implement
    ui-forge repair
    ui-forge verify
    ui-forge review
    ui-forge approve
    ui-forge release
    ui-forge report

Чат использует тот же underlying API/state machine, что и CLI. Нельзя создавать отдельную «магическую» логику только для AI-чата: операции должны быть воспроизводимы локально и в CI.

# 32. Модель оценки кандидата

Не следует сводить качество к одному проценту похожести. Нужен vector score/status:
- structural;
- visual/perceptual;
- responsive;
- interaction;
- accessibility;
- regression;
- performance (informational или policy-controlled).

Hard failure по interaction не может быть компенсирован высоким visual similarity.

Автоматический цикл использует score для convergence, но human review получает объяснимые категории и конкретные diffs.

# 33. Roadmap перехода от текущего пилота

## Stage A — доказать фундамент
Текущая задача Courier Control:
- зелёный CI;
- reproducible visual baseline;
- deterministic fixtures;
- стабильный WebKit/Chromium;
- удобные artifacts;
- staging parity.

## Stage B — Design Contract v0
- schema для screen/component intent;
- reference metadata;
- approval manifest;
- связать baseline с contract revision;
- отделить design approval от implementation approval.

## Stage C — Intelligent diff
- region segmentation;
- DOM bounding-box overlay;
- source ownership;
- BEFORE/AFTER/DIFF report;
- classification workflow.

## Stage D — Scenario/UI Graph
- route discovery;
- named deterministic scenarios;
- role-aware auth;
- generated smoke/geometry tests;
- impact analysis.

## Stage E — Agentic repair loop
- defect localization;
- minimal patch planner;
- automatic rerun;
- regression-aware rollback;
- iteration budget;
- REVIEW_READY state.

## Stage F — Conversational design workflow
- multi-variant proposal generation;
- mixed feedback («A header + C cards»);
- Design Contract creation from approved proposal;
- design revision history;
- handoff directly into implementation agent.

## Stage G — Standalone platform
- extract Hardoffx/ui-forge;
- framework adapters;
- stable config/schema;
- CLI/API;
- reusable GitHub Actions;
- onboarding via ui-forge init.

## Stage H — Full product UX
Пользователь работает почти полностью на уровне:

    «Покажи варианты»
        ↓
    «Вариант C»
        ↓
    «Шапку из A»
        ↓
    «Утверждаю дизайн»
        ↓
    [autonomous implementation + verification]
        ↓
    «Покажи настоящую страницу»
        ↓
    «Сделай кнопку темнее»
        ↓
    [automatic repair + verification]
        ↓
    «Оставляем»
        ↓
    [release pipeline]

# 34. Критерии успеха продукта

UI Forge достигает целевой формы, когда:
1. пользователь может заказать redesign без знания тестовой инфраструктуры;
2. утверждённый дизайн превращается в versioned contract;
3. агент способен самостоятельно приблизить реальный frontend к contract;
4. система обнаруживает функционально сломанный UI даже при идеальном screenshot;
5. unintended regression локализуется до component/source;
6. большинство промежуточных implementation iterations не требуют участия человека;
7. человек видит реальную staging-страницу и небольшое число осмысленных diffs;
8. production никогда не является экспериментальной средой;
9. любой релиз воспроизводим по manifests/commit/contracts;
10. подключение нового проекта требует преимущественно declarative config/adapters, а не копирования инфраструктуры.

# 35. Главный продуктовый принцип

**UI Forge не должен быть AI, который умеет рисовать интерфейс. Он должен быть автономным UI-инженером и системой доказательства корректности результата.**

Генерация красивого изображения — начало процесса. Ценность появляется тогда, когда система способна превратить утверждённое намерение в настоящий работающий frontend, самостоятельно обнаруживать и исправлять расхождения, доказать отсутствие непреднамеренных регрессий, показать человеку проверяемый результат и безопасно провести его до production.
