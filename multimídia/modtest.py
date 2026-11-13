import sys
from playwright.sync_api import sync_playwright
MODS=['Catálogo de módulos','File Info','Recorder','Help','Normalização','Backup da biblioteca','File Editor / Cue Points','BPM Counter','History','Playlist Archive','Window Manager','Sample Editor','Loop Sampler','Sample Player','Mixer','Sair','Diagnostics']
REMOVED=['Audio I/O','Armazenamento','Options','MP3 Stream','CD Player / Writer','Remote Control','Servidor','Keyboard Shortcuts','Skins','Usuários','BPM Print Designer','Compressor / Limiter']
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':900,'height':400}); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('file://'+sys.argv[1]); pg.wait_for_timeout(1200)
    def openm(v):
        return pg.evaluate("(v)=>{try{handleAction('openModule',{dataset:{value:v}});const m=document.querySelector('#modalBack');const o=m&&m.classList.contains('open');const t=document.querySelector('#modalTitle')?.textContent||'';try{closeModal()}catch(e){};return [o,t]}catch(e){return ['ERR '+e.message]}}",v)
    print('RESTANTES:')
    for v in MODS: print(' ',v,openm(v))
    print('REMOVIDAS (não devem quebrar):')
    for v in REMOVED: print(' ',v,openm(v))
    # catálogo: cada launcher
    pg.evaluate("()=>handleAction('openModule',{dataset:{value:'Catálogo de módulos'}})")
    n=pg.evaluate("()=>[...document.querySelectorAll('[data-module-launch]')].length");print('launchers no catálogo:',n)
    bad=pg.evaluate("""()=>{const out=[];for(const b of document.querySelectorAll('[data-module-launch]')){try{b.click();try{closeModal()}catch(e){}; if(!document.querySelector('#modalBack'))out.push('x')}catch(e){out.push(b.dataset.moduleLaunch+': '+e.message)}
      try{handleAction('openModule',{dataset:{value:'Catálogo de módulos'}})}catch(e){}}return out}""");print('launchers com erro:',bad)
    pg.evaluate("()=>{const x=document.querySelector('#bbpm-sample-editor.open [data-se=close]');x&&x.click()}")
    # Escape fecha modal; Space não deve tocar
    pg.evaluate("()=>handleAction('openModule',{dataset:{value:'Help'}})"); pg.keyboard.press('Escape'); pg.wait_for_timeout(200)
    print('modal fechou com Esc:',not pg.evaluate("()=>document.querySelector('#modalBack').classList.contains('open')"))
    pg.set_input_files('#audioFileInput','/home/claude/t.wav'); pg.wait_for_timeout(1500)
    pg.keyboard.press('Space'); pg.wait_for_timeout(300)
    print('Space tocou deck A (esperado False):',pg.evaluate("()=>state.decks.A.playing"))
    print('pageerrors:',errs); b.close()
