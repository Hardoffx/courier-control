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
