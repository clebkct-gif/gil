import sys,struct,math
from playwright.sync_api import sync_playwright
path=sys.argv[1];res=[]
def ok(n,c,x=''):
    res.append(bool(c));print(('OK   ' if c else 'FALHA'),n,x)
def parse_wav(b):
    assert b[:4]==b'RIFF' and b[8:12]==b'WAVE'
    ch=struct.unpack('<H',b[22:24])[0];sr=struct.unpack('<I',b[24:28])[0];bits=struct.unpack('<H',b[34:36])[0];n=struct.unpack('<I',b[40:44])[0]
    d=struct.unpack('<%dh'%(n//2),b[44:44+n]);return ch,sr,bits,n,d
with sync_playwright() as p:
    b=p.chromium.launch(args=['--autoplay-policy=no-user-gesture-required']); ctx=b.new_context(viewport={'width':932,'height':430},accept_downloads=True); pg=ctx.new_page(); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e)[:140]))
    pg.goto('file://'+path); pg.wait_for_timeout(700); pg.evaluate("()=>document.querySelector('#launchApp').click()"); pg.wait_for_timeout(700)
    pg.set_input_files('#audioFileInput',['/home/claude/se_src.wav']); pg.wait_for_timeout(2500)
    pg.evaluate("()=>{showPanel(null);state.selectedTrack=tracks[0].id;audioEngine.loadId(tracks[0].id,'A');renderAll()}"); pg.wait_for_timeout(1200)
    # 1) abre pelo menu Sampler
    pg.evaluate("()=>{document.querySelector('[data-menu=Sampler]').click()}"); pg.wait_for_timeout(150)
    pg.evaluate("()=>[...document.querySelectorAll('#menuPopup button')].find(b=>/Sample Editor/.test(b.textContent)).click()"); pg.wait_for_timeout(1500)
    ok('menu Sampler > Sample Editor abre o editor',pg.evaluate("()=>document.querySelector('#bbpm-sample-editor').classList.contains('open')"))
    srcs=pg.evaluate("()=>[...document.querySelectorAll('#seSource option')].map(o=>o.textContent)");print('     origens:',srcs)
    ok('origem lista o Deck A com o título da música',any(s.startswith('Deck A') for s in srcs))
    ok('o áudio foi lido e a forma de onda desenhada',pg.evaluate("()=>{const c=document.querySelector('#seCanvas'),d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;let n=0;for(let i=0;i<d.length;i+=4)if(d[i+2]>150&&d[i]<120)n++;return n>200}"))
    nm0=pg.evaluate("()=>document.querySelector('#seName').value")
    # 2) campos início/fim
    pg.fill('#seStart','0:02.000');pg.press('#seStart','Tab');pg.fill('#seEnd','0:04.000');pg.press('#seEnd','Tab');pg.wait_for_timeout(200)
    dur=pg.evaluate("()=>document.querySelector('#seDur').textContent");ok('digitar início e fim define a duração',dur.strip()=='2.000 s',dur)
    ok('o nome sugerido acompanha o trecho',pg.evaluate("()=>document.querySelector('#seName').value")!=nm0 and '0:02' in pg.evaluate("()=>document.querySelector('#seName').value"),pg.evaluate("()=>document.querySelector('#seName').value"))
    # 3) batidas
    pg.fill('#seBpm','120');pg.press('#seBpm','Tab');pg.click('[data-se=b4]');pg.wait_for_timeout(150)
    ok('botão 4 batidas a 120 BPM = 2,000 s (e liga o loop sincronizado)',pg.evaluate("()=>document.querySelector('#seDur').textContent.trim()")=='2.000 s' and pg.evaluate("()=>document.querySelector('#seLoop').checked"),pg.evaluate("()=>document.querySelector('#seBeats').textContent"))
    pg.click('[data-se=b8]');pg.wait_for_timeout(150);ok('botão 8 batidas = 4,000 s',pg.evaluate("()=>document.querySelector('#seDur').textContent.trim()")=='4.000 s')
    pg.click('[data-se=b4]')
    # 4) arrastar a barra do fim
    box=pg.evaluate("()=>{const r=document.querySelector('#seCanvas').getBoundingClientRect();return [r.x,r.y,r.width,r.height]}")
    ex=pg.evaluate("()=>{return Math.round(document.querySelector('#seEnd').value.length)}")
    pg.click('[data-se=zall]');pg.wait_for_timeout(150)
    # posição x do fim (4 s de 12 s) com o início em 2 s
    W=box[2];x_end=box[0]+W*(4.0/12.0)
    pg.mouse.move(x_end,box[1]+box[3]/2);pg.mouse.down();pg.mouse.move(x_end+W*(1.0/12.0),box[1]+box[3]/2,steps=6);pg.mouse.up();pg.wait_for_timeout(200)
    endv=pg.evaluate("()=>document.querySelector('#seEnd').value");print('     fim depois de arrastar:',endv)
    ok('arrastar a barra laranja move o fim (~5 s)',endv.startswith('0:05.0') or endv.startswith('0:04.9') or endv.startswith('0:05.1'),endv)
    # ajuste fino
    pg.click('[data-se=he]');pg.click('[data-se="n-100"]');pg.click('[data-se="n-100"]');pg.click('[data-se="n+10"]');pg.wait_for_timeout(150)
    # volta para 2–4 s
    pg.fill('#seStart','0:02.000');pg.press('#seStart','Tab');pg.fill('#seEnd','0:04.000');pg.press('#seEnd','Tab');pg.wait_for_timeout(150)
    # 5) ouvir
    pg.click('[data-se=play]');pg.wait_for_timeout(700)
    ok('Ouvir liga a pré-escuta em loop (botão vira Parar)',pg.evaluate("()=>document.querySelector('[data-se=play]').textContent.includes('Parar')"))
    pg.click('[data-se=play]');pg.wait_for_timeout(200)
    ok('Parar desliga a pré-escuta',pg.evaluate("()=>document.querySelector('[data-se=play]').textContent.includes('Ouvir')"))
    # 6) exportar WAV
    pg.fill('#seName','Meu Loop');
    with pg.expect_download() as dl: pg.click('[data-se=wav]')
    d=dl.value;pth=d.path();raw=open(pth,'rb').read()
    ch,sr,bits,n,data=parse_wav(raw)
    print('     WAV: arquivo',d.suggested_filename,'| canais',ch,'| taxa',sr,'| bits',bits,'| amostras',len(data),'=',round(len(data)/sr,3),'s')
    ok('o WAV exportado tem nome certo, 16 bits e ~2,000 s',d.suggested_filename=='Meu Loop.wav' and bits==16 and abs(len(data)/sr-2.0)<0.01)
    rms=lambda a:math.sqrt(sum(x*x for x in a)/max(1,len(a)))/32768
    ok('o conteúdo é o trecho certo (tom de 440 Hz presente, bordas suavizadas)',rms(data[sr//2:sr//2+2000])>0.25 and abs(data[0])<500 and abs(data[-1])<500,f"rms={rms(data[sr//2:sr//2+2000]):.2f} bordas={data[0]},{data[-1]}")
    # trecho silencioso → comparação: 4–6 s deve estar em silêncio
    pg.fill('#seStart','0:04.500');pg.press('#seStart','Tab');pg.fill('#seEnd','0:05.500');pg.press('#seEnd','Tab')
    with pg.expect_download() as dl2: pg.click('[data-se=wav]')
    _,_,_,_,d2=parse_wav(open(dl2.value.path(),'rb').read());ok('um trecho silencioso exporta silêncio',rms(d2)<0.01,f"rms={rms(d2):.4f}")
    # normalizar
    pg.fill('#seStart','0:06.000');pg.press('#seStart','Tab');pg.fill('#seEnd','0:08.000');pg.press('#seEnd','Tab');pg.check('#seNorm')
    with pg.expect_download() as dl3: pg.click('[data-se=wav]')
    _,_,_,_,d3=parse_wav(open(dl3.value.path(),'rb').read());mx=max(abs(x) for x in d3)/32768
    ok('Normalizar leva o pico a ~0,98',0.96<=mx<=0.99,f"pico={mx:.3f}");pg.uncheck('#seNorm')
    # 7) salvar no slot 5, como loop
    pg.fill('#seStart','0:02.000');pg.press('#seStart','Tab');pg.fill('#seEnd','0:04.000');pg.press('#seEnd','Tab');pg.fill('#seName','Tom 440')
    pg.select_option('#seSlot','4');pg.check('#seLoop');pg.click('[data-se=save]');pg.wait_for_timeout(1500)
    s=pg.evaluate("()=>({src:!!sampleDecks[4].src,name:sampleNames[4],mode:sampleModes[4],dur:Math.round(sampleDecks[4].duration*100)/100})")
    ok('Salvar no slot 5 carrega o sample (nome, loop e duração 2 s)',s['src'] and s['name']=='Tom 440' and s['mode']=='loop' and abs((s['dur'] or 0)-2.0)<0.1,str(s))
    # slot ocupado pede confirmação
    pg.select_option('#seSlot','4');pg.click('[data-se=save]');pg.wait_for_timeout(400)
    ok('slot ocupado pede confirmação antes de substituir (e o aviso aparece por cima do editor)',pg.evaluate("()=>{const d=document.querySelector('.bbpm-dlg');if(!d)return false;const r=d.getBoundingClientRect(),e=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return d.contains(e)}"))
    pg.evaluate("()=>document.querySelector('.bbpm-dlg .row button:first-child')?.click()");pg.wait_for_timeout(300);pg.evaluate("()=>document.querySelectorAll('.bbpm-dlg-back').forEach(e=>e.remove())")
    # 8) Esc fecha
    pg.keyboard.press('Escape');pg.wait_for_timeout(200)
    ok('Esc fecha o editor',not pg.evaluate("()=>document.querySelector('#bbpm-sample-editor').classList.contains('open')"))
    # 9) persistência do slot depois de recarregar
    pg.reload();pg.wait_for_timeout(1500);pg.evaluate("()=>document.querySelector('#launchApp').click()");pg.wait_for_timeout(1500)
    s2=pg.evaluate("()=>({src:!!sampleDecks[4].src,name:sampleNames[4],mode:sampleModes[4]})")
    ok('o sample do slot 5 continua depois de reabrir o app',s2['src'] and s2['name']=='Tom 440' and s2['mode']=='loop',str(s2))
    # 10) menu de contexto da faixa
    pg.evaluate("()=>{showPanel(null);document.querySelector('[data-zoom=list]').click()}");pg.wait_for_timeout(500)
    r=pg.query_selector_all('#libraryList .trackrow')[0];bx=r.bounding_box();pg.mouse.click(bx['x']+bx['width']/2,bx['y']+bx['height']/2,button='right');pg.wait_for_timeout(300)
    ok('menu de contexto tem "Criar sample…"',pg.evaluate("()=>!!document.querySelector('[data-track-cmd=sample]')"))
    pg.evaluate("()=>document.querySelector('[data-track-cmd=sample]').click()");pg.wait_for_timeout(1500)
    ok('Criar sample… abre o editor já com a faixa',pg.evaluate("()=>document.querySelector('#bbpm-sample-editor').classList.contains('open')&&/Faixa|Deck|Selecionada/.test(document.querySelector('#seSource').selectedOptions[0].textContent)&&document.querySelector('#seDur').textContent.includes('s')"))
    # 11) loop do deck e "aqui"
    pg.evaluate("()=>{state.decks.A.loop=true;state.decks.A.loopStart=6;state.decks.A.loopEnd=8}")
    pg.evaluate("()=>{const s=document.querySelector('#seSource');const o=[...s.options].find(o=>o.value==='A');if(o){s.value='A';s.dispatchEvent(new Event('change'))}}");pg.wait_for_timeout(1500)
    pg.click('[data-se=deckloop]');pg.wait_for_timeout(200)
    ok('Loop do deck copia o trecho do loop (6 → 8 s)',pg.evaluate("()=>document.querySelector('#seStart').value")=='0:06.000' and pg.evaluate("()=>document.querySelector('#seEnd').value")=='0:08.000')
    pg.evaluate("()=>{audioEngine.decks.A.audio.currentTime=3.5}");pg.click('[data-se=here-s]');pg.wait_for_timeout(150)
    ok('⏺ Início aqui usa a posição atual do deck (3,5 s)',pg.evaluate("()=>document.querySelector('#seStart').value")=='0:03.500')
    # 12) carregar arquivo comum no sample continua funcionando
    pg.keyboard.press('Escape')
    pg.evaluate("()=>{state.selectedSamplePad=1}");pg.set_input_files('#sampleFileInput','/home/claude/m1.wav');pg.wait_for_timeout(1500)
    ok('carregar arquivo no Sample Player (função refatorada) continua funcionando',pg.evaluate("()=>!!sampleDecks[1].src&&sampleNames[1]==='m1.wav'"))
    print('erros de página:',errs);ok('sem erros de página',not errs)
    b.close()
print('RESUMO:',sum(res),'de',len(res))
