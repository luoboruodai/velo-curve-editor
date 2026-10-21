"""Native settings, theme editing and explicit preset-save transactions."""
import json
import math
import re
import base64
import tempfile
from pathlib import Path

TABS=('interface','presets','theme','graph')
INPUTS=('save_name','save_text','grid_x','grid_y','hex_curve','hex_background','hex_handles')
CHOICES=('loc_left','loc_right','loc_top','loc_bottom','page_interface','page_presets','page_theme','page_graph',
         'compact','motion','auto_load','show_speed','import','export','theme_edit','fit','reset',
         'thumb_graph','thumb_text','thumb_image','choose_image','cancel','confirm','close',
         'color_blue','color_cyan','color_amber','export_keyframes')
SLIDERS=('box_size','precision','speed_strength')
TOGGLE=('compact','motion','auto_load','show_speed')


def catalogue():
    spec={}
    for name in ('backdrop','panel','header_line','footer_line','section1','section2','section3','section4','swatch_curve','swatch_background','swatch_handles','preview_image'):
        spec['dlg_'+name]=('surface','')
    for name in ('title','legend1','legend2','legend3','legend4','message','row1','row2','row3','row4','row5','row6','row7','row8','preview_text'):
        spec['dlg_'+name]=('text','')
    spec['dlg_backdrop_hit']=('hit','')
    for name in CHOICES:
        spec['dlg_'+name]=('hit','')
        spec['dlg_'+name+'_bg']=('surface','')
        spec['dlg_'+name+'_label']=('text','')
    for name in INPUTS:
        spec['dlg_'+name]=('input','')
        spec['dlg_'+name+'_bg']=('surface','')
    for name in TOGGLE:spec['dlg_'+name+'_knob']=('surface','')
    for name in SLIDERS:
        for part,kind in (('track','surface'),('knob','surface'),('hit','slider'),('value','text')):
            spec['dlg_'+name+'_'+part]=(kind,'')
    return spec

NAMES=tuple(catalogue())
HIT_LAYERS={name:(101 if name=='dlg_backdrop_hit' else 110)
            for name,(kind,_) in catalogue().items() if kind in ('hit','slider')}


def logic(c):return c.op('curve_logic').module

def cache(c):return logic(c).st(c)

def node(c,name):return c.op('dlg_'+name)

def text(c,name,value):logic(c).set_node_text(c,'dlg_'+name,str(value))

def visible(c,name,on):logic(c).set_visible(c,'dlg_'+name,on)


def open_modal(c,kind):
    m=logic(c);q=cache(c)
    q['modal_kind']=kind;q['settings_open']=kind=='settings';q['dialog_page']=q.get('dialog_page','interface')
    q['dialog_message']=''
    q['input_values']={};q['field_initialized']=set()
    if kind=='save':
        q.update({'save_type':'graph','save_image_node':None,'save_snapshot':m.state_from_component(c)})
        for name,value in (('save_name','预设 %02d'%(len(m.user_presets(c))+1)),('save_text','Preset')):
            node(c,name).par.text=value;q['input_values'][name]=value
    if kind=='theme':
        s=m.state_from_component(c);q['theme_before']={k:s[k] for k in ('theme_color','theme_background','theme_handles')}
    sync(c)


def close_modal(c):
    q=cache(c);q['modal_kind']=None;q['settings_open']=False
    sync(c)


def reset_inputs(c,*names):
    q=cache(c)
    for name in names:
        q.setdefault('input_values',{}).pop(name,None)
        q.setdefault('field_initialized',set()).discard(name)


def input_changed(c,name,value):
    name=name.removeprefix('dlg_');q=cache(c);q.setdefault('input_values',{})[name]=str(value)
    if name in ('grid_x','grid_y'):
        try:
            m=logic(c);s=m.state_from_component(c);s[name]=int(value)
            if not 1<=s[name]<=20:raise ValueError('grid range')
            m.assign_state(c,s);q['dialog_message']='';reset_inputs(c,name);refresh(c)
        except (ValueError,TypeError):q['dialog_message']='网格数量请输入 1–20 的整数'
    elif name.startswith('hex_'):
        key={'hex_curve':'theme_color','hex_background':'theme_background','hex_handles':'theme_handles'}[name]
        if re.fullmatch(r'#[0-9a-fA-F]{6}',str(value)):
            m=logic(c);s=m.state_from_component(c);s[key]=str(value);m.assign_state(c,s);q['dialog_message']='';refresh(c)
        else:q['dialog_message']='颜色格式示例：#4a90e2'
    sync(c)


def input_value(c,name):
    return cache(c).get('input_values',{}).get(name,str(node(c,name).par.text.eval())).strip()


def refresh(c):
    m=logic(c)
    m.update(c);m.layout_ui(c);c.op('graph_engine').module.apply_visuals(c)


def action(c,name):
    m=logic(c);q=cache(c)
    if name=='settings_open':
        if q.get('modal_kind'):close_modal(c)
        else:open_modal(c,'settings')
        return True
    if name=='action_save':open_modal(c,'save');return True
    if name=='settings_close':close_modal(c);return True
    if name in ('preset_prev_page','preset_next_page'):
        pages=max(1,math.ceil(len(m.preset_entries(c))/16));q['preset_page']=(q.get('preset_page',0)+(1 if name=='preset_next_page' else -1))%pages
        refresh(c);return True
    if name=='preset_apply':
        pending=q.pop('pending_preset',None)
        if pending:m.button(c,pending)
        return True
    if c.op('graph_engine').module.action(c,name):return True
    if not name.startswith('dlg_'):return False
    key=name[4:]
    if key in ('close','cancel'):
        if q.get('modal_kind')=='theme' and key=='cancel':
            s=m.state_from_component(c);s.update(q.get('theme_before',{}));m.assign_state(c,s);refresh(c)
        close_modal(c);return True
    s=m.state_from_component(c)
    if key.startswith('page_'):q['dialog_page']=key[5:]
    elif key.startswith('loc_'):s['preset_location']=key[4:];m.assign_state(c,s);refresh(c)
    elif key in TOGGLE:
        field={'compact':'compact','motion':'reduce_motion','auto_load':'auto_load_preset','show_speed':'show_speed'}[key]
        s[field]=not s[field];m.assign_state(c,s);refresh(c)
    elif key.startswith('thumb_'):q['save_type']=key[6:]
    elif key=='theme_edit':open_modal(c,'theme')
    elif key=='choose_image':choose_image(c)
    elif key=='confirm':
        if q.get('modal_kind')=='save':save_preset(c)
        else:close_modal(c)
    elif key in ('import','export'):preset_file(c,key)
    elif key=='export_keyframes':c.op('keyframe_export').module.export(c)
    elif key=='fit':c.op('graph_engine').module.action(c,'view_fit')
    elif key=='reset':
        for field in m.UI_KEYS:s[field]=m.DEFAULTS[field]
        reset_inputs(c,'grid_x','grid_y');q['dialog_message']=''
        m.assign_state(c,s);refresh(c)
    elif key.startswith('color_'):
        s['theme_color']={'color_blue':'#4a90e2','color_cyan':'#39c5cf','color_amber':'#f2b35d'}[key]
        reset_inputs(c,'hex_curve');q['dialog_message']=''
        m.assign_state(c,s);refresh(c)
    sync(c);return True


def slider(c,name):
    key=name.removeprefix('dlg_').removesuffix('_hit')
    m=logic(c);s=m.state_from_component(c);hit=node(c,key+'_hit')
    ratio=m.clamp(float(hit.panel.u),0,1)
    field,lo,hi={'box_size':('preset_size',40.,104.),'precision':('precision',50,1000),'speed_strength':('speed_strength',.05,.65)}[key]
    s[field]=lo+(hi-lo)*ratio
    m.assign_state(c,s);refresh(c)


def choose_image(c):
    path=ui.chooseFile(load=True,fileTypes=['png','jpg','jpeg','webp'],title='选择预设缩略图')
    if not path:return
    q=cache(c)
    try:
        name='preset_image_%02d'%(len(logic(c).user_presets(c))+1)
        # Keep the bitmap inside this component, not an external file dependency.
        top=c.create(moviefileinTOP,name);top.par.file=path;top.cook(force=True)
        if top.errors() or top.width<=0:raise ValueError('无法解码图片')
        top.lock=True;top.par.file=''
        q['save_image_node']=top.name;q['dialog_message']='图片已嵌入组件'
    except Exception as err:q['dialog_message']='图片读取失败：'+str(err)
    sync(c)


def save_preset(c):
    m=logic(c);q=cache(c);name=input_value(c,'save_name')
    if not name:q['dialog_message']='请填写预设名称';sync(c);return
    thumb={'type':q.get('save_type','graph')}
    if thumb['type']=='text':thumb['value']=input_value(c,'save_text') or name
    if thumb['type']=='image':
        if not q.get('save_image_node'):q['dialog_message']='请先选择缩略图';sync(c);return
        thumb['node']=q['save_image_node']
    entries=list(m.user_presets(c))
    entries.append({'name':name[:80],'curve':dict(q['save_snapshot']),'thumbnail':thumb})
    payload=json.dumps(entries,ensure_ascii=False,separators=(',',':'),allow_nan=False)
    # Native DAT payload limits are real. Do not silently truncate older presets.
    if len(payload.encode('utf-8'))>60000:q['dialog_message']='预设库接近宿主大小限制，请先导出备份';sync(c);return
    if not persist_library(c,entries):sync(c);return
    c.op('user_presets').text=payload;q['preset_page']=(len(m.preset_entries(c))-1)//16
    close_modal(c);q['points']=None;refresh(c);m.set_status(c,'已保存预设 · '+name)


def preset_file(c,kind,entries=None,path=None):
    m=logic(c);q=cache(c)
    if path is None:
        path=ui.chooseFile(load=kind=='import',fileTypes=['json'],title='导入曲线预设' if kind=='import' else '导出曲线预设',start='Velo_Presets.json' if kind=='export' else None)
    if not path:return False
    try:
        if kind=='export':
            entries=json.loads(json.dumps(m.user_presets(c) if entries is None else entries))
            for entry in entries:
                thumb=entry.get('thumbnail',{})
                if thumb.get('type')=='image' and c.op(thumb.get('node','')):
                    with tempfile.TemporaryDirectory(prefix='velo-thumb-') as tmp:
                        png=Path(tmp)/'thumbnail.png';c.op(thumb['node']).save(str(png))
                        thumb['png_base64']=base64.b64encode(png.read_bytes()).decode('ascii')
            Path(path).write_text(json.dumps({'format':'velo-presets','version':3,'presets':entries},ensure_ascii=False,indent=2),encoding='utf-8')
            q['dialog_message']='已导出 %d 个曲线预设'%len(entries);m.set_status(c,q['dialog_message'])
        else:
            data=json.loads(Path(path).read_text(encoding='utf-8'));incoming=data.get('presets',[]) if isinstance(data,dict) else data
            if not isinstance(incoming,list):raise ValueError('不是有效预设列表')
            old=m.user_presets(c);validated=[]
            for i,item in enumerate(incoming):
                if not isinstance(item,dict) or 'curve' not in item or not isinstance(item.get('name'),str):raise ValueError('预设缺少名称或曲线')
                entry={'name':item['name'][:80],'curve':m.normalized_state(item['curve']),'thumbnail':dict(item.get('thumbnail',{'type':'graph'}))}
                thumb=entry['thumbnail']
                if thumb.get('type')=='image' and thumb.get('png_base64'):
                    image=base64.b64decode(thumb.pop('png_base64'),validate=True)
                    with tempfile.TemporaryDirectory(prefix='velo-thumb-') as tmp:
                        png=Path(tmp)/'thumb.png';png.write_bytes(image)
                        top=c.create(moviefileinTOP,'preset_image_import_%02d'%(len(old)+i+1));top.par.file=str(png);top.cook(force=True)
                        if top.errors():raise ValueError('缩略图无法读取')
                        top.lock=True;top.par.file='';thumb['node']=top.name
                elif thumb.get('type')=='image':thumb={'type':'graph'};entry['thumbnail']=thumb
                validated.append(entry)
            payload=json.dumps(old+validated,ensure_ascii=False,separators=(',',':'),allow_nan=False)
            if len(payload.encode('utf-8'))>60000:raise ValueError('导入后超过宿主预设库大小限制')
            if not persist_library(c,old+validated):sync(c);return False
            c.op('user_presets').text=payload;q['dialog_message']='已导入 %d 个曲线预设'%len(validated);m.set_status(c,q['dialog_message']);refresh(c)
    except Exception as err:q['dialog_message']='操作未完成：'+str(err);m.set_status(c,q['dialog_message'])
    sync(c)
    return True



def backdrop(c):
    q=cache(c);hit=node(c,'backdrop_hit');rect=q.get('dialog_bounds')
    if not rect:return
    x=float(hit.panel.u)*c.par.w.eval();top=(1-float(hit.panel.v))*c.par.h.eval()
    a,b,w,h=rect
    if not(a<=x<=a+w and b<=top<=b+h):close_modal(c)


def sync(c):
    m=logic(c);q=cache(c)
    if not q.get('legacy_dialogs_hidden'):
        for name in c.op('ui_style').module.MODAL_NAMES:m.set_visible(c,name,False)
        q['legacy_dialogs_hidden']=True
    shown=bool(q.get('modal_kind')) or q.get('modal_amount',0)>0
    if not shown:
        if not q.get('dialogs_hidden'):
            for name in NAMES:m.set_visible(c,name,False)
            q['dialogs_hidden']=True
            q.pop('dialog_layout_key',None)
        return
    layout(c)


def layout(c):
    m=logic(c);q=cache(c);s=m.state_from_component(c);kind=q.get('modal_kind') or q.get('last_modal_kind','settings')
    q['last_modal_kind']=kind;opened=bool(q.get('modal_kind'))
    if not opened and q.get('modal_amount',0)<=0:
        sync(c);return
    width,height=float(c.par.w.eval()),float(c.par.h.eval())
    key=(width,height,kind,opened,q.get('modal_amount',0),tuple(s.items()),
         q.get('dialog_page'),q.get('save_type'),q.get('save_image_node'),
         q.get('dialog_message'),tuple(q.get('input_values',{}).items()),
         frozenset(q.get('field_initialized',())),
         tuple(q.get('dtoggle_'+name) for name in TOGGLE))
    if q.get('dialog_layout_key')==key:return
    q['dialog_layout_key']=key;q['dialogs_hidden']=False
    full=False
    pw=min(392.,width-24)
    section_heights={'interface':114,'presets':124,'theme':80,'graph':174}
    if kind=='settings':
        page=q.get('dialog_page','interface')
        # Content + 16px breathing room + fixed footer; no large empty slab.
        ph=min(section_heights.get(page,100)+148.,height-20.)
    else:
        ph=min(350.,height-20.)
    if kind=='theme':ph=min(320.,height-20.)
    x,y=(width-pw)/2,(height-ph)/2
    a=q.get('modal_amount',0);scale=.95+.05*a;cx,cy=width/2,height/2
    rects={};labels={};shown=set()
    def place(name,rx,ry,rw,rh):
        n='dlg_'+name;shown.add(n)
        rects[n]=(cx+(rx-cx)*scale,cy+(ry-cy)*scale,rw*scale,rh*scale)
    def label(name,value,rx,ry,rw,rh=20):
        labels[name]=str(value);place(name,rx,ry,rw,rh)
    accent=c.op('graph_engine').module.rgb(s['theme_color'])
    def button(name,value,rx,ry,rw,rh=28,selected=False):
        for suffix in ('','_bg','_label'):place(name+suffix,rx,ry,rw,rh)
        labels[name+'_label']=value
        q.setdefault('dialog_targets',{})[name]=accent if selected else ((.235,)*3)
    def toggle(name,value,rx,ry):
        button(name,'',rx,ry,40,20,value)
        if not value:q['dialog_targets'][name]=(.14,.14,.14)
        t=q.get('dtoggle_'+name,float(value));place(name+'_knob',rx+3+20*t,ry+3,14,14)
    def field(name,value,rx,ry,rw,rh=23):
        place(name+'_bg',rx,ry,rw,rh)
        place(name,rx+6,ry,rw-12,rh)
        initialized=q.setdefault('field_initialized',set())
        if name not in initialized:
            node(c,name).par.text=q.get('input_values',{}).get(name,str(value));initialized.add(name)
    def rail(name,value,lo,hi,rx,ry,rw):
        ratio=m.clamp((value-lo)/(hi-lo),0,1)
        place(name+'_track',rx,ry+10,rw,5);place(name+'_knob',rx+ratio*rw-7.5,ry+5,15,15);place(name+'_hit',rx-5,ry,rw+10,25)
        label(name+'_value',('%.0f'%value if name!='speed_strength' else '%.0f%%'%(100*value)),rx+rw+8,ry,44,23)
    for name in ('backdrop','backdrop_hit'):m.place(c,'dlg_'+name,0,0,width,height);shown.add('dlg_'+name)
    place('panel',x,y,pw,ph);place('header_line',x+1,y+39,pw-2,1);place('footer_line',x+1,y+ph-44,pw-2,1)
    label('title',{'settings':'设置','save':'保存预设  Save Preset','theme':'主题编辑器  Theme'}[kind],x+16,y+9,pw-62,25)
    button('close','×',x+pw-36,y+7,27,27)
    q['dialog_targets']={k:v for k,v in q.get('dialog_targets',{}).items() if k=='close'}
    if kind=='settings':
        sections=[q.get('dialog_page','interface')]
        if not full:
            for i,key in enumerate(TABS):button('page_'+key,('界面','预设','主题','图形')[i],x+12+i*(pw-24)/4,y+48,(pw-30)/4,28,key in sections)
        sy=y+(55 if full else 88);sx=x+14;sw=pw-28
        heights=section_heights
        for idx,key in enumerate(sections):
            h=heights[key];place('section%d'%(idx+1),sx,sy,sw,h)
            label('legend%d'%(idx+1),{'interface':'界面设置','presets':'预设管理','theme':'主题设置','graph':'图形设置'}[key],sx+10,sy+4,120,14)
            # A transparent in-section caption gets its own space instead of
            # resembling a second tab or overlapping the content below.
            sy += 16
            if key=='interface':
                label('row1','预设位置',sx+10,sy+12,75)
                for i,loc in enumerate(('left','right','top','bottom')):button('loc_'+loc,('左','右','上','下')[i],sx+91+i*(sw-101)/4,sy+10,(sw-107)/4,26,s['preset_location']==loc)
                label('row2','紧凑模式',sx+10,sy+41,sw-70);toggle('compact',s['compact'],sx+sw-53,sy+40)
                label('row3','减少动效',sx+10,sy+69,sw-70);toggle('motion',s['reduce_motion'],sx+sw-53,sy+68)
            elif key=='presets':
                label('row4','拖拽排序 · 右键删除 / 导出',sx+10,sy+11,sw-20)
                label('row5','卡片大小',sx+10,sy+39,65);rail('box_size',s['preset_size'],40,104,sx+78,sy+35,max(46,sw-137))
                button('import','导入曲线预设',sx+10,sy+66,(sw-25)/2,32);button('export','导出曲线预设',sx+15+(sw-25)/2,sy+66,(sw-25)/2,32)
            elif key=='theme':button('theme_edit','打开主题编辑器  ›',sx+10,sy+12,sw-20,36)
            else:
                label('row6','网格 X / Y',sx+10,sy+11,90);field('grid_x',s['grid_x'],sx+112,sy+8,48);field('grid_y',s['grid_y'],sx+168,sy+8,48)
                label('row7','曲线精度',sx+10,sy+42,70);rail('precision',s['precision'],50,1000,sx+80,sy+36,max(44,sw-138))
                label('row8','贝塞尔速度背景',sx+10,sy+73,sw-70);toggle('show_speed',s['show_speed'],sx+sw-53,sy+69)
                rail('speed_strength',s['speed_strength'],.05,.65,sx+80,sy+98,max(44,sw-138))
                label('preview_text','强度',sx+10,sy+103,65)
                button('export_keyframes','写入关键帧',sx+10,sy+126,sw-20,28,True)
            sy += h+12
        button('reset','恢复默认',x+14,y+ph-38,(pw-34)/2,32);button('fit','适配当前曲线',x+20+(pw-34)/2,y+ph-38,(pw-34)/2,32,True)
    elif kind=='save':
        label('row1','预设名称',x+16,y+53,82);field('save_name','',x+104,y+50,pw-120)
        place('section1',x+14,y+90,pw-28,76);label('legend1','Thumbnail Type  缩略图',x+24,y+82,184,19)
        tw=(pw-46)/3
        for i,key in enumerate(('graph','text','image')):button('thumb_'+key,('曲线','文字','图片')[i],x+22+i*(tw+2),y+112,tw,30,q.get('save_type')==key)
        typ=q.get('save_type','graph')
        if typ=='text':field('save_text','',x+22,y+182,pw-44,30);label('preview_text',input_value(c,'save_text'),x+22,y+218,pw-44,30)
        elif typ=='image':
            button('choose_image','选择图片…',x+22,y+182,pw-44,29)
            if q.get('save_image_node'):
                place('preview_image',x+pw/2-38,y+220,76,40);node(c,'preview_image').par.top=q['save_image_node']
        else:
            place('preview_image',x+22,y+178,pw-44,85);node(c,'preview_image').par.top='plot_render'
        label('message',q.get('dialog_message','取消不会新增预设'),x+18,y+ph-72,pw-36,22)
        button('cancel','取消',x+14,y+ph-34,(pw-34)/2,28);button('confirm','保存',x+20+(pw-34)/2,y+ph-34,(pw-34)/2,28,True)
    else:
        for i,(key,title) in enumerate((('curve','曲线颜色'),('background','画布背景'),('handles','控制点颜色'))):
            sy=y+59+i*47;label('row%d'%(i+1),title,x+17,sy,94)
            statekey={'curve':'theme_color','background':'theme_background','handles':'theme_handles'}[key]
            field('hex_'+key,s[statekey],x+112,sy-3,pw-163,26);place('swatch_'+key,x+pw-40,sy,22,22)
            for ch,value in zip('rgb',rgb(s[statekey])):node(c,'swatch_'+key).par['bgcolor'+ch]=value
        for i,key in enumerate(('blue','cyan','amber')):button('color_'+key,('蓝色','青色','琥珀')[i],x+17+i*(pw-34)/3,y+213,(pw-40)/3,27)
        label('message',q.get('dialog_message','输入 #RRGGBB，可实时预览'),x+17,y+ph-72,pw-34,22)
        button('cancel','取消',x+14,y+ph-34,(pw-34)/2,28);button('confirm','完成',x+20+(pw-34)/2,y+ph-34,(pw-34)/2,28,True)
    if kind=='settings' and q.get('dialog_message'):label('message',q['dialog_message'],x+16,y+ph-65,pw-32,18)
    for name in NAMES:
        n=c.op(name);on=name in shown;m.set_visible(c,name,on)
        if n:
            # TD 2025.31550 initializes generated Button COMPs at layer 0.
            # Restore modal input ordering after load, before exposing the hit.
            layer=HIT_LAYERS.get(name)
            if layer is not None and float(n.par.layer.eval())!=layer:n.par.layer=layer
            if abs(float(n.par.opacity.eval())-a)>1e-6:n.par.opacity=a
            enabled=bool(on and (opened or name=='dlg_backdrop_hit'))
            if bool(n.par.enable.eval())!=enabled:n.par.enable=enabled
    for name,rect in rects.items():m.place(c,name,*rect)
    for name,value in labels.items():text(c,name,value)
    q['dialog_rects']=dict(rects)
    q['dialog_bounds']=rects['dlg_panel']


def rgb(value):return tuple(int(value[i:i+2],16)/255 for i in (1,3,5))


def motion(c,dt):
    q=cache(c)
    if not q.get('modal_kind') and q.get('modal_amount',0)<=0:
        sync(c);return
    m=logic(c);u=c.op('ui_style').module;s=m.state_from_component(c)
    target=float(bool(q.get('modal_kind')))
    amount=u.tween(q,'modal',target,dt,.2,s['reduce_motion'],0.)
    q['modal_amount']=amount
    for key,field in (('compact','compact'),('motion','reduce_motion'),('auto_load','auto_load_preset'),('show_speed','show_speed')):
        q['dtoggle_'+key]=u.tween(q,'dlg_toggle_'+key,float(s[field]),dt,.4,s['reduce_motion'])
    if target or amount>0:
        layout(c)
        for key,base in q.get('dialog_targets',{}).items():
            hit=node(c,key)
            color=tuple(min(1,v+.04) for v in base) if hit and hit.panel.rollover else base
            if hit and hit.panel.lselect:color=tuple(v*.82 for v in color)
            current=u.tween(q,'dlg_color_'+key,color,dt,.15,s['reduce_motion'])
            bg=node(c,key+'_bg')
            for ch,value in zip('rgb',current):
                if abs(float(bg.par['bgcolor'+ch].eval())-value)>1e-6:bg.par['bgcolor'+ch]=value
    else:sync(c)


def library_path(c):
    # Explicitly saved presets survive component replacement; no background process or network.
    override=cache(c).get('library_override')
    return Path(override) if override else Path.home()/'.velo_curve_editor'/'presets.json'


def persist_library(c,entries):
    q=cache(c)
    try:
        export=json.loads(json.dumps(entries))
        for entry in export:
            thumb=entry.get('thumbnail',{})
            if thumb.get('type')=='image' and c.op(thumb.get('node','')):
                with tempfile.TemporaryDirectory(prefix='velo-thumb-') as tmp:
                    png=Path(tmp)/'thumb.png';c.op(thumb['node']).save(str(png))
                    thumb['png_base64']=base64.b64encode(png.read_bytes()).decode('ascii')
        path=library_path(c);path.parent.mkdir(parents=True,exist_ok=True)
        value=json.dumps({'format':'velo-presets','version':3,'presets':export},ensure_ascii=False,allow_nan=False)
        temporary=path.with_suffix('.tmp');temporary.write_text(value,encoding='utf-8');temporary.replace(path)
        return True
    except Exception as err:q['dialog_message']='预设未保存：'+str(err);return False


def load_library(c):
    q=cache(c)
    if q.get('library_loaded'):return
    q['library_loaded']=True
    path=library_path(c)
    if not path.is_file():return
    m=logic(c)
    try:
        incoming=json.loads(path.read_text(encoding='utf-8'))['presets']
        current=list(m.user_presets(c))
        def signature(entry):return entry['name']+m.dumps_state(m.normalized_state(entry['curve']))
        seen={signature(item) for item in current}
        for item in incoming:
            if signature(item) in seen:continue
            thumb=item.get('thumbnail',{})
            if thumb.get('type')=='image' and thumb.get('png_base64'):
                with tempfile.TemporaryDirectory(prefix='velo-thumb-') as tmp:
                    png=Path(tmp)/'thumb.png';png.write_bytes(base64.b64decode(thumb.pop('png_base64')))
                    top=c.create(moviefileinTOP,'preset_image_library_%02d'%(len(current)+1));top.par.file=str(png);top.cook(force=True)
                    if top.errors():raise ValueError('预设图片解码失败')
                    top.lock=True;top.par.file='';thumb['node']=top.name
            current.append(item);seen.add(signature(item))
        payload=json.dumps(current,ensure_ascii=False,separators=(',',':'),allow_nan=False)
        if len(payload.encode('utf-8'))>60000:raise ValueError('预设数量超过组件限制，请从备份导入所需部分')
        c.op('user_presets').text=payload;q['layout_key']=None;q['points']=None
    except Exception as err:m.set_status(c,'预设库读取未完成：'+str(err))
