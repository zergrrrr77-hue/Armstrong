# Claude 프로젝트로 옮기는 방법

## 1. 프로젝트 만들기
1. 컴퓨터 브라우저에서 claude.ai에 로그인합니다.
2. 왼쪽 메뉴에서 **Projects(프로젝트)** → **Create project(새 프로젝트)**를 누릅니다.
3. 이름(예: `잊혀진 대장간`)을 입력하고 만듭니다.

## 2. 지침 넣기
1. 프로젝트 화면 오른쪽의 **Instructions(지침)** → 편집을 누릅니다.
2. `00_PROJECT_INSTRUCTIONS.md` 파일의 내용을 전부 복사해 붙여 넣고 저장합니다.

## 3. 지식 파일 올리기
1. 프로젝트 화면의 **Project knowledge(프로젝트 지식)** → **+** → 파일 업로드를 누릅니다.
2. 아래 파일을 올립니다.
   - 01_ARCHIVE_MASTER.md
   - 02_game_template.html.txt
   - 03_art_tools_bundle.py.txt
   - 04_sound_engine_sfx.js.txt
   - 05_tests_bundle.js.txt
   - 06_docs_bundle.md
   - 07_asset_meta.json.txt
   - images 폴더의 PNG 10장(카탈로그 5장 + 게임 화면 5장)
3. 용량이 꽉 찼다고 나오면 05(테스트)부터 빼세요. 01 → 02 → 06 → 07 순서로 중요합니다.

## 4. 시작하기
프로젝트 안에서 새 대화를 열고 이렇게 말해 보세요.
> "01_ARCHIVE_MASTER.md를 읽고 지금까지 만든 걸 요약해 줘. 그다음 새로 만들 방향을 같이 정하자."

## 알아 둘 점
- 프로젝트는 **대화 공간**이라 코드를 읽고 새로 써 줄 수는 있지만, 실행하거나 저장소에 올리지는 못합니다. 실제 개발과 실행은 Claude Code(GitHub 저장소 연결)에서 하세요.
- 실제 그림·소리 파일(수천 개)은 프로젝트에 넣지 않습니다. 에셋 팩 ZIP과 GitHub 보관 브랜치에 그대로 있습니다.
