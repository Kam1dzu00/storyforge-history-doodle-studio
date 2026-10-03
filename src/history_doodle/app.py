from __future__ import annotations

import logging, os, shutil, sys, time
from pathlib import Path
from PySide6.QtCore import QObject, QSize, QThread, Signal, Qt, QUrl, QTimer
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QComboBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QProgressBar, QPushButton, QScrollArea, QSpinBox, QSplitter, QTabWidget, QTextEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget
from .config import DEFAULT_VOICE, LOGS_DIR, PROJECTS_DIR, STYLE_REFERENCE, VOICES, ensure_dirs
from .health import check
from .pipeline import Pipeline
from .planner import build_shot_prompt
from .storage import ProjectStore
from .util import setup_logging

class Worker(QObject):
    progress=Signal(str); done=Signal(object); failed=Signal(str)
    def __init__(self, fn): super().__init__(); self.fn=fn
    def run(self):
        try: self.done.emit(self.fn())
        except Exception as exc: logging.exception("Background task failed"); self.failed.emit(str(exc))

class Window(QMainWindow):
    def __init__(self):
        super().__init__(); ensure_dirs(); self.store=ProjectStore(); self.project:Path|None=None; self.started=0.0
        self.setWindowTitle("History Doodle Studio"); self.resize(1440,900); self._ui(); self.refresh_projects(); self.timer=QTimer(self); self.timer.timeout.connect(self.tick)

    def _ui(self):
        root=QWidget(); root.setObjectName("root"); self.setCentralWidget(root); outer=QVBoxLayout(root); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        header=QFrame(); header.setObjectName("header"); hh=QHBoxLayout(header); hh.setContentsMargins(24,14,24,14)
        brand=QLabel("HISTORY DOODLE  <span style='color:#8b95a5'>STUDIO</span>"); brand.setObjectName("brand"); hh.addWidget(brand); hh.addStretch(); self.header_project=QLabel("Проект не выбран"); self.header_project.setObjectName("muted"); hh.addWidget(self.header_project); system=QPushButton("Проверить систему"); system.setObjectName("quiet"); system.clicked.connect(self.system_check); hh.addWidget(system); outer.addWidget(header)
        split=QSplitter(); split.setHandleWidth(1); outer.addWidget(split,1)

        left=QFrame(); left.setObjectName("sidebar"); lv=QVBoxLayout(left); lv.setContentsMargins(16,18,16,18); lv.setSpacing(10)
        label=QLabel("ВАШИ ПРОЕКТЫ"); label.setObjectName("eyebrow"); lv.addWidget(label)
        new=QPushButton("＋  Новый ролик"); new.setObjectName("secondary"); new.clicked.connect(self.new_project); lv.addWidget(new)
        self.projects=QListWidget(); self.projects.setObjectName("projectList"); self.projects.itemClicked.connect(self.open_project); lv.addWidget(self.projects,1)
        steps=QLabel("ЭТАПЫ СОЗДАНИЯ"); steps.setObjectName("eyebrow"); lv.addWidget(steps)
        self.stage_labels={}
        for key,text in [("script","Сценарий"),("planning","Раскадровка"),("voice","Озвучка"),("images","Иллюстрации"),("subtitles","Субтитры"),("render","Готовое видео")]:
            item=QLabel(text); item.setObjectName("stage"); lv.addWidget(item); self.stage_labels[key]=item
        split.addWidget(left)

        center_scroll=QScrollArea(); center_scroll.setObjectName("workspaceScroll"); center_scroll.setWidgetResizable(True); center_scroll.setFrameShape(QFrame.NoFrame)
        center=QWidget(); center.setObjectName("workspace"); cv=QVBoxLayout(center); cv.setContentsMargins(28,24,28,28); cv.setSpacing(16); center_scroll.setWidget(center)
        welcome=QLabel("Создайте исторический ролик"); welcome.setObjectName("h1"); cv.addWidget(welcome)
        hint=QLabel("Введите идею или вставьте готовый сценарий. Студия сама создаст раскадровку, английскую озвучку, иллюстрации, субтитры и итоговое видео — полностью локально на вашем Mac."); hint.setWordWrap(True); hint.setObjectName("muted"); cv.addWidget(hint)
        self.title=QLineEdit(); self.title.setPlaceholderText("Название ролика, например: Чем викинги занимались весь день?"); self.title.setObjectName("titleInput"); cv.addWidget(self.title)
        self.tabs=QTabWidget(); self.tabs.setObjectName("inputTabs"); self.brief=QTextEdit(); self.brief.setPlaceholderText("Опишите тему, тон, важные факты и для кого этот ролик…"); self.script=QTextEdit(); self.script.setPlaceholderText("Вставьте готовый английский текст рассказчика…"); self.tabs.addTab(self.brief,"У меня есть идея"); self.tabs.addTab(self.script,"У меня есть сценарий"); cv.addWidget(self.tabs,3)
        settings=QFrame(); settings.setObjectName("card"); form=QFormLayout(settings); form.setContentsMargins(18,16,18,16); form.setSpacing(12)
        self.duration=QSpinBox(); self.duration.setRange(1,60); self.duration.setValue(10); self.duration.setSuffix(" мин"); self.voice=QComboBox(); self.voice.addItems(VOICES); self.music=QLineEdit(); self.music.setPlaceholderText("Необязательно — оставьте пустым для одной озвучки"); music_btn=QPushButton("Выбрать"); music_btn.setObjectName("quiet"); music_btn.clicked.connect(self.choose_music); row=QHBoxLayout(); row.addWidget(self.music); row.addWidget(music_btn)
        locked=QLabel("History Doodle · взрослый редакционный мультфильм"); locked.setObjectName("chip"); form.addRow("Длительность",self.duration); form.addRow("Голос рассказчика",self.voice); form.addRow("Фоновая музыка",row); form.addRow("Стиль канала",locked); cv.addWidget(settings)
        self.primary=QPushButton("Создать готовое видео — весь процесс"); self.primary.setObjectName("primary"); self.primary.clicked.connect(self.run_next); cv.addWidget(self.primary)
        self.cancel_button=QPushButton("Отменить безопасно"); self.cancel_button.setObjectName("quiet"); self.cancel_button.clicked.connect(self.cancel_job); self.cancel_button.hide(); cv.addWidget(self.cancel_button)
        advanced=QFrame(); advanced.setObjectName("card"); av=QVBoxLayout(advanced); av.addWidget(QLabel("Ручное управление этапами")); buttons=QHBoxLayout(); self.stage_buttons=[]
        for text,stage in [("Сценарий","create_script"),("Раскадровка","plan_video"),("Озвучка","generate_voice"),("Картинки","generate_images"),("Субтитры","build_subtitles"),("Сборка","render_video")]:
            b=QPushButton(text); b.setObjectName("quiet"); b.clicked.connect(lambda _,s=stage:self.run_stage(s)); buttons.addWidget(b); self.stage_buttons.append(b)
        av.addLayout(buttons); rebuild=QPushButton("Пересобрать раскадровку после изменения сценария"); rebuild.setObjectName("quiet"); rebuild.clicked.connect(self.rebuild_scenes); av.addWidget(rebuild); cv.addWidget(advanced)
        self.progress=QProgressBar(); self.progress.setTextVisible(False); self.progress.setFixedHeight(5); self.progress.hide(); cv.addWidget(self.progress)
        self.status=QLabel("Готово к работе"); self.status.setObjectName("status"); cv.addWidget(self.status); split.addWidget(center_scroll)
        self.project_info=QLabel("Слов: 0 · Голос: — · Сцен: 0 · Кадров: 0 · Изображения: 0 / 0 · Видео: не собрано"); self.project_info.setObjectName("muted"); cv.addWidget(self.project_info)

        right=QFrame(); right.setObjectName("inspector"); rv=QVBoxLayout(right); rv.setContentsMargins(18,18,18,18); rv.setSpacing(10)
        story_title=QLabel("РАСКАДРОВКА И ПРОСМОТР"); story_title.setObjectName("eyebrow"); rv.addWidget(story_title)
        self.tree=QTreeWidget(); self.tree.setHeaderHidden(True); self.tree.itemClicked.connect(self.show_item); rv.addWidget(self.tree,2)
        self.grid=QListWidget(); self.grid.setViewMode(QListWidget.IconMode); self.grid.setIconSize(QSize(150,84)); self.grid.setResizeMode(QListWidget.Adjust); self.grid.setSpacing(8); self.grid.setMaximumHeight(245); self.grid.itemClicked.connect(self.show_grid_item); rv.addWidget(self.grid)
        self.preview=QLabel("Здесь появится выбранный сгенерированный кадр"); self.preview.setObjectName("preview"); self.preview.setAlignment(Qt.AlignCenter); self.preview.setMinimumHeight(230); self.preview.setWordWrap(True); rv.addWidget(self.preview)
        self.shot_meta=QLabel(""); self.shot_meta.setObjectName("muted"); self.shot_meta.setWordWrap(True); rv.addWidget(self.shot_meta)
        self.visual_type=QComboBox(); self.visual_type.addItems(["CHARACTER_WIDE","CHARACTER_MEDIUM","CHARACTER_CLOSEUP","OBJECT_HERO","OBJECT_COLLECTION","DETAIL","ENVIRONMENT","INFO_CARD","MAP","COMPARISON","SILHOUETTE","GROUP"]); self.visual_type.currentTextChanged.connect(self.change_visual_type); rv.addWidget(self.visual_type)
        self.details=QTextEdit(); self.details.setPlaceholderText("Выберите сцену или кадр, чтобы посмотреть и изменить описание."); rv.addWidget(self.details,1)
        save=QPushButton("Сохранить описание кадра"); save.setObjectName("quiet"); save.clicked.connect(self.save_prompt); rv.addWidget(save)
        actions=QHBoxLayout(); same=QPushButton("Повторить точно"); same.setToolTip("Сгенерировать кадр повторно с тем же числом случайности"); same.setObjectName("quiet"); same.clicked.connect(lambda:self.regen(False)); regen=QPushButton("Новый вариант"); regen.clicked.connect(lambda:self.regen(True)); actions.addWidget(same); actions.addWidget(regen); rv.addLayout(actions)
        shot_actions=QHBoxLayout(); open_image=QPushButton("Открыть изображение"); open_image.setObjectName("quiet"); open_image.clicked.connect(self.open_image); preview_scene=QPushButton("Превью сцены"); preview_scene.setObjectName("quiet"); preview_scene.clicked.connect(self.preview_selected_scene); shot_actions.addWidget(open_image); shot_actions.addWidget(preview_scene); rv.addLayout(shot_actions)
        openv=QPushButton("▶  Открыть готовое видео"); openv.setObjectName("secondary"); openv.clicked.connect(self.open_video); rv.addWidget(openv)
        tools=QHBoxLayout(); finder=QPushButton("Показать файлы"); finder.setObjectName("quiet"); finder.clicked.connect(self.show_finder); style=QPushButton("Референс стиля"); style.setObjectName("quiet"); style.clicked.connect(self.replace_style_reference); tools.addWidget(finder); tools.addWidget(style); rv.addLayout(tools); split.addWidget(right); split.setSizes([235,780,425]); split.setCollapsible(0,False); split.setCollapsible(1,False)
        self.setStyleSheet("""
            *{font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text';font-size:14px;color:#eef2f6}
            QWidget#root,QWidget#workspace,QScrollArea#workspaceScroll,QScrollArea#workspaceScroll>QWidget>QWidget{background:#0b0e12} QFrame#header{background:#10151b;border-bottom:1px solid #232b35} QFrame#sidebar,QFrame#inspector{background:#10151b} QFrame#sidebar{border-right:1px solid #232b35} QFrame#inspector{border-left:1px solid #232b35}
            QLabel#brand{font-size:17px;font-weight:800;letter-spacing:1px} QLabel#h1{font-size:30px;font-weight:800} QLabel#eyebrow{font-size:11px;font-weight:700;color:#758294;letter-spacing:1px} QLabel#muted{color:#98a3b2} QLabel#status{background:#141a21;border:1px solid #27313d;border-radius:10px;padding:12px;color:#b9c3cf} QLabel#stage{padding:8px 10px;border-radius:8px;color:#778393} QLabel#stage[complete='true']{color:#a7dfb4;background:#14231a} QLabel#chip{color:#d8ab69;background:#2a2117;border:1px solid #4e3a23;border-radius:8px;padding:8px}
            QLabel#stage[failed='true']{color:#ff9d9d;background:#321919} QLabel#stage[stale='true']{color:#e2b765;background:#2d2415}
            QFrame#card{background:#121820;border:1px solid #29333f;border-radius:14px} QTextEdit,QLineEdit,QListWidget,QTreeWidget,QComboBox,QSpinBox{background:#11171e;border:1px solid #303b48;border-radius:10px;padding:9px;selection-background-color:#d79847;selection-color:#111} QLineEdit#titleInput{font-size:17px;font-weight:600;padding:13px} QTextEdit:focus,QLineEdit:focus,QListWidget:focus,QTreeWidget:focus,QComboBox:focus,QSpinBox:focus{border:1px solid #d79847}
            QListWidget#projectList{padding:4px} QListWidget::item{padding:10px;border-radius:8px;margin:2px} QListWidget::item:selected{background:#263140;color:white} QTreeWidget::item{padding:6px} QTreeWidget::item:selected{background:#263140}
            QTabWidget::pane{border:1px solid #29333f;border-radius:12px;background:#11171e;top:-1px} QTabBar::tab{background:transparent;color:#8490a0;padding:10px 16px;border-bottom:2px solid transparent} QTabBar::tab:selected{color:#fff;border-bottom:2px solid #d79847}
            QPushButton{min-height:40px;background:#222b35;border:1px solid #384553;border-radius:10px;padding:0 14px;font-weight:600} QPushButton:hover{background:#2b3743;border-color:#536273} QPushButton:pressed{background:#1d252e;padding-top:1px} QPushButton#primary{min-height:54px;background:#d79847;border-color:#e4aa5d;color:#17120b;font-size:16px;font-weight:800} QPushButton#primary:hover{background:#e5a753} QPushButton#secondary{background:#243241;border-color:#3b5066} QPushButton#quiet{background:transparent;color:#aeb8c5;border-color:#2c3641}
            QLabel#preview{background:#0b0f14;border:1px solid #303b48;border-radius:12px;color:#687586;padding:8px} QProgressBar{background:#1a2028;border:0;border-radius:2px} QProgressBar::chunk{background:#d79847;border-radius:2px} QSplitter::handle{background:#232b35}
        """)

    def refresh_projects(self):
        self.projects.clear();
        for p in sorted(PROJECTS_DIR.glob("*/project.json")):
            try: title=self.store.load_state(p.parent).title
            except Exception: title=p.parent.name.replace("-"," ").title()
            row=QListWidgetItem(title); row.setData(Qt.UserRole,str(p.parent)); row.setToolTip(str(p.parent)); self.projects.addItem(row)
    def new_project(self):
        title=self.title.text().strip() or "Untitled History Video"; mode="brief" if self.tabs.currentIndex()==0 else "script"; text=(self.brief if mode=="brief" else self.script).toPlainText().strip()
        if not text: return QMessageBox.warning(self,"Не хватает текста","Сначала опишите идею или вставьте готовый сценарий.")
        self.project=self.store.create(title,mode,self.duration.value()*60,self.voice.currentText(),text); self.refresh_projects(); self.load_project()
    def open_project(self,item): self.project=Path(item.data(Qt.UserRole)); self.load_project()
    def load_project(self):
        if not self.project:return
        state=self.store.load_state(self.project); self.title.setText(state.title); self.duration.setValue(state.target_duration_seconds//60); self.voice.setCurrentText(state.voice); self.music.setText(state.background_music or "")
        for name,widget in [("brief.txt",self.brief),("script.txt",self.script)]:
            p=self.project/name
            if p.exists(): widget.setPlainText(p.read_text(encoding="utf-8"))
        self.header_project.setText(state.title); self.refresh_tree(); self.update_stage_rail(state); self.status.setText(f"Открыт проект: {state.title}"); self.update_project_info(state)
    def update_project_info(self,state):
        script=(self.project/"script.txt").read_text(encoding="utf-8") if (self.project/"script.txt").exists() else ""; scenes=shots=ready=failed=0; voice="—"
        if (self.project/"planning/story.json").exists():
            plan=self.store.load_plan(self.project); scenes=len(plan.scenes); shots=len(plan.shots); ready=sum(x.status=="complete" for x in plan.shots); failed=sum(x.status=="failed" for x in plan.shots)
        if (self.project/"audio/narration.wav").exists():
            from .audio import audio_duration
            seconds=audio_duration(self.project/"audio/narration.wav"); voice=f"{int(seconds//60):02d}:{int(seconds%60):02d}"
        video="готово" if state.render_status=="complete" else "не собрано"
        self.project_info.setText(f"Слов: {len(script.split())} · Голос: {voice} · Сцен: {scenes} · Кадров: {shots} · Изображения: {ready} / {shots} · Ошибок: {failed} · Видео: {video}")
    def update_stage_rail(self,state):
        for key,label in self.stage_labels.items():
            status=getattr(state,f"{key}_status",""); done=status=="complete"; label.setProperty("complete",done); label.setProperty("failed",status=="failed"); label.setProperty("stale",status=="stale"); symbol="✓" if done else "!" if status=="failed" else "↻" if status=="stale" else "○"; label.setText(symbol+"  "+label.text().lstrip("✓!↻○ 0123456789")); label.style().unpolish(label); label.style().polish(label)
        complete=state.render_status=="complete"
        self.primary.setText("Открыть готовое видео" if complete else "Создать готовое видео — весь процесс")
    def run_next(self):
        if not self.project:
            self.new_project()
            if self.project: self.run_stage("full")
            return
        state=self.store.load_state(self.project)
        if state.render_status=="complete": return self.open_video()
        self.run_stage("full")
    def _ensure(self):
        if not self.project:self.new_project()
        if not self.project:raise RuntimeError("Создайте или выберите проект")
        state=self.store.load_state(self.project); state.voice=self.voice.currentText(); state.background_music=self.music.text().strip() or None
        if (self.project/"script.txt").exists(): (self.project/"script.txt").write_text(self.script.toPlainText(),encoding="utf-8")
        self.store.save_state(self.project,state)
    def run_stage(self,name):
        try:self._ensure()
        except Exception as e:return QMessageBox.warning(self,"Проект",str(e))
        self.started=time.time(); self.last_message="Запускаю этап…"; self.timer.start(1000); self.progress.setRange(0,0); self.progress.show(); self.primary.setEnabled(False); self.cancel_button.show(); self.active_pipeline=Pipeline(self.project,lambda m:self.worker.progress.emit(m)); fn=getattr(self.active_pipeline,name); self.thread=QThread(); self.worker=Worker(fn); self.worker.moveToThread(self.thread); self.thread.started.connect(self.worker.run); self.worker.progress.connect(self.update_status); self.worker.done.connect(self.finish); self.worker.failed.connect(self.fail); self.worker.done.connect(self.thread.quit); self.worker.failed.connect(self.thread.quit); self.thread.start()
    def update_status(self,text): self.last_message=text; self.tick()
    def tick(self):
        if hasattr(self,"started") and self.started:self.status.setText(f"{getattr(self,'last_message','Работаю…')}  •  прошло {int(time.time()-self.started)} сек.")
    def finish(self,result):
        self.timer.stop(); self.progress.hide(); self.primary.setEnabled(True); self.cancel_button.hide(); self.cancel_button.setEnabled(True); self.status.setText("Этап завершён"); self.load_project()
        if isinstance(result,Path) and result.exists(): QDesktopServices.openUrl(QUrl.fromLocalFile(str(result)))
    def fail(self,error): self.timer.stop(); self.progress.hide(); self.primary.setEnabled(True); self.cancel_button.hide(); self.status.setText("Нужно исправить ошибку"); QMessageBox.critical(self,"Не удалось завершить этап",error+"\n\nТехнические подробности сохранены в logs/app.log")
    def cancel_job(self):
        if getattr(self,"active_pipeline",None): self.active_pipeline.cancel(); self.cancel_button.setEnabled(False); self.status.setText("Отмена после безопасного сохранения текущей операции…")
    def refresh_tree(self):
        self.tree.clear(); self.grid.clear()
        if not self.project or not (self.project/"planning/story.json").exists():return
        plan=self.store.load_plan(self.project); scenes={x.id:x for x in plan.scenes}; shots={x.id:x for x in plan.shots}
        for sec in plan.sections:
            a=QTreeWidgetItem([sec.title]); a.setData(0,Qt.UserRole,("section",sec.id)); self.tree.addTopLevelItem(a)
            for sid in sec.scene_ids:
                sc=scenes[sid]; b=QTreeWidgetItem([f"Сцена {sc.order}"]); b.setData(0,Qt.UserRole,("scene",sc.id)); a.addChild(b)
                for shid in sc.shot_ids:
                    sh=shots[shid]; status={"complete":"готов","pending":"ожидает","stale":"нужно обновить","generating":"создаётся","failed":"ошибка"}.get(sh.status,sh.status); c=QTreeWidgetItem([f"Кадр {sh.order} · {status}"]); c.setData(0,Qt.UserRole,("shot",sh.id)); b.addChild(c)
                    duration=(sh.end_time-sh.start_time) if sh.start_time is not None and sh.end_time is not None else sh.estimated_duration; tile=QListWidgetItem(f"Кадр {sh.order}\n{duration:.1f} сек · {status.upper()}"); tile.setData(Qt.UserRole,sh.id)
                    if sh.image_path and (self.project/sh.image_path).exists(): tile.setIcon(QIcon(str(self.project/sh.image_path)))
                    self.grid.addItem(tile)
        self.tree.expandAll()
    def show_grid_item(self,item):
        ident=item.data(Qt.UserRole); proxy=QTreeWidgetItem(); proxy.setData(0,Qt.UserRole,("shot",ident)); self.show_item(proxy)
    def show_item(self,item):
        if not self.project:return
        kind,ident=item.data(0,Qt.UserRole); plan=self.store.load_plan(self.project)
        if kind=="scene": self.current_scene=ident; self.details.setPlainText(next(x.narration_text for x in plan.scenes if x.id==ident))
        elif kind=="shot":
            sh=next(x for x in plan.shots if x.id==ident); self.details.setPlainText(sh.prompt); self.current_shot=ident
            self.current_scene=sh.scene_id
            names={c.id:c.name for c in plan.characters}; people=", ".join(names.get(x,x) for x in sh.character_ids) or "нет"
            self.shot_meta.setText(f"Тип: {sh.visual_type} · Людей: {sh.people_count} · Объекты: {', '.join(sh.objects) or 'нет'} · Персонажи: {people} · Движение: {sh.camera_motion} · Время: {sh.start_time or 0:.1f}–{sh.end_time or 0:.1f} сек. · Seed: {sh.seed}")
            self.visual_type.blockSignals(True); self.visual_type.setCurrentText(sh.visual_type); self.visual_type.blockSignals(False)
            if sh.image_path:
                pix=QPixmap(str(self.project/sh.image_path)); self.preview.setPixmap(pix.scaled(self.preview.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation))
    def save_prompt(self):
        if not self.project or not getattr(self,"current_shot",None):return
        plan=self.store.load_plan(self.project); sh=next(x for x in plan.shots if x.id==self.current_shot); sh.prompt=self.details.toPlainText(); sh.status="stale"; self.store.save_plan(self.project,plan); self.refresh_tree()
    def change_visual_type(self,value):
        if not self.project or not getattr(self,"current_shot",None): return
        plan=self.store.load_plan(self.project); sh=next(x for x in plan.shots if x.id==self.current_shot); sh.visual_type=value; sh.director_override=True
        no_people=value in {"OBJECT_HERO","OBJECT_COLLECTION","DETAIL","ENVIRONMENT","INFO_CARD","MAP"}
        sh.people_count=0 if no_people else max(1,sh.people_count)
        if no_people: sh.character_ids=[]
        elif not sh.character_ids and plan.characters: sh.character_ids=[plan.characters[0].id]
        build_shot_prompt(sh,{c.id:c for c in plan.characters}); sh.status="stale"; sh.prompt_hash=None
        self.store.save_plan(self.project,plan); state=self.store.load_state(self.project); state.images_status="stale"; state.render_status="stale"; self.store.save_state(self.project,state); self.details.setPlainText(sh.prompt); self.refresh_tree()
    def regen(self,new_seed=True):
        if getattr(self,"current_shot",None): self.run_custom(lambda:Pipeline(self.project,lambda m:self.worker.progress.emit(m)).generate_images(self.current_shot,new_seed))
    def open_image(self):
        if self.project and getattr(self,"current_shot",None):
            sh=next(x for x in self.store.load_plan(self.project).shots if x.id==self.current_shot)
            if sh.image_path: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.project/sh.image_path)))
    def preview_selected_scene(self):
        if self.project and getattr(self,"current_scene",None): self.run_custom(lambda:Pipeline(self.project,lambda m:self.worker.progress.emit(m)).preview_scene(self.current_scene))
    def run_custom(self,fn):
        self.started=time.time(); self.last_message="Working…"; self.timer.start(1000); self.thread=QThread(); self.worker=Worker(fn); self.worker.moveToThread(self.thread); self.thread.started.connect(self.worker.run); self.worker.progress.connect(self.update_status); self.worker.done.connect(self.finish); self.worker.failed.connect(self.fail); self.worker.done.connect(self.thread.quit); self.worker.failed.connect(self.thread.quit); self.thread.start()
    def choose_music(self):
        p,_=QFileDialog.getOpenFileName(self,"Выберите фоновую музыку","","Аудио (*.mp3 *.wav *.m4a)");
        if p:self.music.setText(p)
    def open_video(self):
        if self.project:QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.project/"render/final_video.mp4")))
    def show_finder(self):
        if self.project:os.system(f"open -R '{self.project/'render/final_video.mp4'}'")
    def system_check(self):
        data=check(); QMessageBox.information(self,"Проверка системы","\n".join(f"{k}: {('ГОТОВО' if v is True else 'ОШИБКА' if v is False else v)}" for k,v in data.items()))
    def rebuild_scenes(self):
        if not self.project:return
        (self.project/"script.txt").write_text(self.script.toPlainText(),encoding="utf-8"); state=self.store.load_state(self.project); state.script_status="complete"; state.planning_status="pending"; state.images_status="stale"; state.subtitles_status="stale"; state.render_status="stale"; self.store.save_state(self.project,state); self.run_stage("plan_video")
    def replace_style_reference(self):
        p,_=QFileDialog.getOpenFileName(self,"Выберите референс стиля","","Изображения (*.png *.jpg *.jpeg *.webp)")
        if p:
            STYLE_REFERENCE.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,STYLE_REFERENCE); QMessageBox.information(self,"Стиль канала","Референс заменён. Он будет направлять будущие генерации, а зафиксированный текстовый стиль останется неизменным.")

def main():
    ensure_dirs(); setup_logging(LOGS_DIR/"app.log"); app=QApplication(sys.argv)
    app.setApplicationName("History Doodle Studio")
    app.setApplicationDisplayName("History Doodle Studio")
    icon = Path(__file__).resolve().parents[2] / "assets" / "app_icon.png"
    if icon.exists(): app.setWindowIcon(QIcon(str(icon)))
    w=Window(); w.setWindowIcon(app.windowIcon()); w.show(); w.raise_(); w.activateWindow(); sys.exit(app.exec())

if __name__=="__main__":main()
