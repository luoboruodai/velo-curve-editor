"""Session/native preset ordering and recoverable built-in visibility."""
import json


def logic(c):
    try:
        return c.op('curve_logic').module
    except AttributeError:
        import curve_logic
        return curve_logic


def reindexed_order(entries):
    """Assign stable order ids after user presets are reindexed."""
    result=[];user_index=0
    for entry_id,_,_ in entries:
        if entry_id.startswith('preset_user_'):
            user_index+=1;result.append('preset_user_%d'%user_index)
        else:
            result.append(entry_id)
    return result


def sort_entries(c,entries):
    m=logic(c);state=m.state_from_component(c)
    by_id={entry[0]:entry for entry in entries}
    hidden=set(state.get('hidden_builtins',[]))
    ordered=[];seen=set()
    for entry_id in list(state.get('preset_order',[]))+list(by_id):
        if entry_id in seen or entry_id not in by_id or entry_id in hidden:continue
        ordered.append(by_id[entry_id]);seen.add(entry_id)
    return ordered


def refresh(c):
    """Recompute page geometry before forcing a fresh catalogue render."""
    m=logic(c);q=m.st(c)
    pages=max(1,(len(m.preset_entries(c))+15)//16)
    q['preset_page']=max(0,min(q.get('preset_page',0),pages-1))
    q['layout_key']=None
    m.layout_ui(c)
    keys=q.setdefault('render_update_keys',{})
    keys.pop('catalogue',None);keys.pop('selection',None)
    m.update(c)


def move(c,source_id,target_slot):
    m=logic(c);q=m.st(c)
    full=list(m.preset_entries(c));page=q.get('preset_page',0);page_entries=m.page_entries(c)
    source_index=next((i for i,entry in enumerate(full) if entry[0]==source_id),None)
    if source_index is None or target_slot is None:return False
    if target_slot>=10**9:
        target_index=len(full)
    elif target_slot>=len(page_entries):
        target_index=min(len(full),page*16+len(page_entries))
    else:
        target_id=page_entries[target_slot][0]
        target_index=next(i for i,entry in enumerate(full) if entry[0]==target_id)
    moved=full.pop(source_index)
    if source_index<target_index:target_index-=1
    target_index=max(0,min(len(full),target_index))
    if target_index==source_index:
        m.set_status(c,'预设位置未改变');return True
    full.insert(target_index,moved)
    if source_id.startswith('preset_user_'):
        # Preserve actual names separately; normalized curve dictionaries do not
        # otherwise carry the library entry name.
        entries=[]
        for entry in full:
            if not entry[0].startswith('preset_user_'):continue
            curve=entry[2]
            entries.append({'name':curve.get('_library_name',curve.get('name','预设')),
                            'curve':{k:v for k,v in curve.items() if k not in ('_thumbnail','_library_name')},
                            'thumbnail':curve.get('_thumbnail',{'type':'graph'})})
        if not c.op('plugin_dialogs').module.persist_library(c,entries):
            m.set_status(c,'预设排序写入失败');return False
        c.op('user_presets').text=json.dumps(entries,ensure_ascii=False,separators=(',',':'),allow_nan=False)
    state=m.state_from_component(c);state['preset_order']=reindexed_order(full)
    m.assign_state(c,state)
    q['selected_preset']=source_id;q['layout_key']=None
    refresh(c)
    m.set_status(c,'已移动预设 · %s → %02d'%(moved[1],target_index+1))
    return True


def delete_builtin(c,name):
    m=logic(c)
    if name not in m.PRESETS:
        m.set_status(c,'该预设不可删除');return False
    state=m.state_from_component(c)
    hidden=list(state.get('hidden_builtins',[]))
    if name not in hidden:hidden.append(name)
    state['hidden_builtins']=hidden;m.assign_state(c,state)
    q=m.st(c)
    if q.get('selected_preset')==name:q.pop('selected_preset',None)
    q.pop('preset_context',None);q['layout_key']=None
    refresh(c)
    m.set_status(c,'已删除内置预设显示 · 恢复默认可还原')
    return True


def delete_user(c,index):
    m=logic(c);presets=list(m.user_presets(c))
    if not 0<=index<len(presets):
        m.set_status(c,'该预设不可删除');return False
    remaining_entries=[entry for entry in m.preset_entries(c) if entry[0]!='preset_user_%d'%(index+1)]
    removed=presets.pop(index)
    payload=json.dumps(presets,ensure_ascii=False,separators=(',',':'),allow_nan=False)
    if not c.op('plugin_dialogs').module.persist_library(c,presets):
        m.set_status(c,'预设库写入失败，未删除');return False
    c.op('user_presets').text=payload
    q=m.st(c);selected=q.get('selected_preset','')
    if selected.startswith('preset_user_'):
        current=int(selected.rsplit('_',1)[1])
        if current==index+1:q.pop('selected_preset',None)
        elif current>index+1:q['selected_preset']='preset_user_%d'%(current-1)
    state=m.state_from_component(c);state['preset_order']=reindexed_order(remaining_entries)
    m.assign_state(c,state)
    q.pop('preset_context',None);q['layout_key']=None
    refresh(c)
    m.set_status(c,'已删除预设 · '+removed.get('name',''))
    return True


def delete_entry(c,entry_id):
    if entry_id.startswith('preset_user_'):
        return delete_user(c,int(entry_id.rsplit('_',1)[1])-1)
    return delete_builtin(c,entry_id)
