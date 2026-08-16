"""Russian Gradio UI mounted on FastAPI with operational probes."""
from __future__ import annotations
import json, os, threading
from contextlib import asynccontextmanager
import gradio as gr
from fastapi import FastAPI, Response
import config
from engine import TTSEngine, cleanup_tmp, load_presets, normalize_audio, validate_stress

os.environ["GRADIO_ANALYTICS_ENABLED"]="False"
engine=TTSEngine(); presets=load_presets()

@asynccontextmanager
async def lifespan(app):
    cleanup_tmp(); threading.Thread(target=_load,daemon=True).start(); yield
def _load():
    try: engine.load()
    except Exception as exc: print(f"Ошибка загрузки модели: {type(exc).__name__}: {exc}",flush=True)
api=FastAPI(lifespan=lifespan)
@api.get("/healthz")
def healthz(): return {"status":"ok"}
@api.get("/readyz")
def readyz(response:Response):
    if not engine.ready: response.status_code=503
    return {"status":"ready" if engine.ready else "loading"}

def inspect_audio(path):
    if not path:return "Аудио ещё не выбрано."
    try:
        normalized,meta,msg=normalize_audio(path); os.unlink(normalized)
        return f"Длительность: {meta['duration']:.2f} с · {meta['sample_rate']} Гц · каналов: {meta['channels']} · {msg}"
    except Exception as e:return f"Ошибка референса: {e}"
def choose(name):return presets[name]
def check_text(text):return validate_stress(text)[1]
def profile(name):
    return {"Быстро":(16,1.5,-1.0),"Баланс":(32,2.0,-1.0),"Качество":(48,2.0,-1.0)}[name]
def generate(ref,ref_text,text,speed,seed,remove,nfe,cfg,sway,cross,rms,history):
    try:
        if not engine.ready: raise RuntimeError("Модель ещё загружается; проверьте состояние готовности.")
        result=engine.synthesize(ref,ref_text,text,{"speed":speed,"seed":seed,"remove_silence":remove,"nfe_step":nfe,"cfg_strength":cfg,"sway_sampling_coef":sway,"cross_fade_duration":cross,"target_rms":rms})
        row={"WAV":result["path"],"генерация_с":round(result["elapsed"],2),"аудио_с":round(result["duration"],2),"RTF":round(result["rtf"],3),"seed":result["seed"],"параметры":result["params"]}
        history=(history or [])[-2:]+[row]
        report=f"Готово за **{result['elapsed']:.2f} с** · результат **{result['duration']:.2f} с** · RTF **{result['rtf']:.3f}** · seed **{result['seed']}**\n\nПараметры: `{json.dumps(result['params'],ensure_ascii=False)}`\n\nТекст после проверки: {result['text']}"
        return result["path"],result["path"],report,history,json.dumps(history,ensure_ascii=False,indent=2)
    except Exception as e:return None,None,f"**Синтез не выполнен:** {e}",history or [],json.dumps(history or [],ensure_ascii=False,indent=2)

css=""".warning{background:#fff3cd;padding:12px;border-left:5px solid #dc3545}.status{background:#eef6ff;padding:12px;border-radius:8px}@media(max-width:700px){.gradio-container{padding:8px!important}}"""
with gr.Blocks(title="F5‑TTS Russian",css=css,js="""()=>{if(!window.isSecureContext){let e=document.getElementById('http-warning');if(e)e.style.display='block'}}""") as demo:
    gr.Markdown(f"# Локальная лаборатория F5‑TTS Russian\n<div class='status'>Модель: <b>{config.MODEL_REPO} / {config.MODEL_VARIANT}</b> · ревизия <code>{config.MODEL_REVISION}</code> · CPU · потоков: {os.getenv('OMP_NUM_THREADS',os.cpu_count())} · готовность: <a href='/readyz'>/readyz</a><br>Генерация на CPU может быть заметно медленнее результата. Лицензия модели: <b>CC BY-NC 4.0, только некоммерческое использование</b>.</div>\n<div class='warning'>Нет авторизации: не публикуйте этот интерфейс в интернете.</div>\n<div id='http-warning' class='warning' style='display:none'>Браузер может заблокировать запись с микрофона на обычном HTTP. Загрузите готовый аудиофайл. Для записи непосредственно в браузере потребуется HTTPS.</div>")
    history=gr.State([])
    gr.Markdown("## 1. Образец голоса\nПрочитайте текст точно, без пропусков и дополнительных слов. Записывайте голос в тихом помещении, без музыки, эха и обработки. Для стихов читайте образец с той выразительностью, которую хотите получить в результате.")
    with gr.Row():
        ref=gr.Audio(label="Записать или загрузить WAV/MP3/FLAC/OGG/M4A",sources=["upload","microphone"],type="filepath")
        with gr.Column():
            ref_text=gr.Textbox(label="Точная расшифровка",value=config.PREPARED_REFERENCE,lines=6)
            reset_ref=gr.Button("Восстановить подготовленный текст")
            audio_info=gr.Markdown("Аудио ещё не выбрано.")
    ref.change(inspect_audio,ref,audio_info); reset_ref.click(lambda:config.PREPARED_REFERENCE,None,ref_text)
    gr.Markdown("## 2. Текст синтеза")
    with gr.Row():
        with gr.Column():
            preset=gr.Dropdown(list(presets),value=list(presets)[0],label="Заготовка")
            text=gr.Textbox(value=presets[list(presets)[0]],label="Редактируемый русский текст",lines=10)
            validation=gr.Markdown(); text.change(check_text,text,validation); preset.change(choose,preset,text)
        gr.Markdown("**Памятка**\n\nСтавьте `+` непосредственно перед ударной гласной: `молок+о`, `з+амок`, `зам+ок`.\n\nНе заменяйте букву **ё** на **е**. Знак `+` влияет на словесное ударение, а пунктуация и переносы — на паузы и интонацию.")
    gr.Markdown("## 3. Настройки\nЭмоциональная манера прежде всего переносится из референсного аудио.")
    with gr.Row():
        prof=gr.Radio(["Быстро","Баланс","Качество"],value="Баланс",label="Профиль")
        speed=gr.Slider(.5,2,1,step=.05,label="Скорость речи")
        seed=gr.Number(-1,precision=0,label="Seed (-1 — случайный)")
        remove=gr.Checkbox(False,label="Удалять длинную тишину")
    with gr.Accordion("Дополнительные настройки",open=False):
        with gr.Row():
            nfe=gr.Slider(8,64,32,step=1,label="nfe_step"); cfg=gr.Slider(0,5,2,step=.1,label="cfg_strength"); sway=gr.Slider(-1,1,-1,step=.1,label="sway_sampling_coef")
            cross=gr.Slider(0,1,.15,step=.05,label="cross_fade_duration"); rms=gr.Slider(.01,.3,.1,step=.01,label="target_rms")
        gr.Markdown("Длинный текст автоматически разбивается F5‑TTS с учётом пауз; рекомендуемый фрагмент — до 135 байт. `fix_duration` намеренно не задаётся: естественная длительность определяется текстом и скоростью.")
    prof.change(profile,prof,[nfe,cfg,sway])
    reset=gr.Button("Восстановить рекомендуемые настройки"); reset.click(lambda:("Баланс",1,-1,False,32,2,-1,.15,.1),None,[prof,speed,seed,remove,nfe,cfg,sway,cross,rms])
    gr.Markdown("## 4. Результат")
    go=gr.Button("Сгенерировать речь",variant="primary")
    with gr.Row(): output=gr.Audio(label="Результат WAV",type="filepath"); download=gr.File(label="Скачать WAV")
    report=gr.Markdown(); gr.Markdown("### До трёх результатов этой вкладки"); history_view=gr.Code(language="json")
    go.click(generate,[ref,ref_text,text,speed,seed,remove,nfe,cfg,sway,cross,rms,history],[output,download,report,history,history_view],concurrency_limit=1)
demo.queue(default_concurrency_limit=1,max_size=20)
api=gr.mount_gradio_app(api,demo,path="/",allowed_paths=[str(config.TMP_DIR)])
if __name__=="__main__":
    import uvicorn; uvicorn.run(api,host="127.0.0.1",port=7860,workers=1,log_level="info")
