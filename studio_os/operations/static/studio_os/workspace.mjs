import {escapeHTML as h, human, formatDate, money, errorText, nairobiInput, fromNairobiInput,
        leadTargets, routeForAction} from "./ui-utils.mjs";

const root = document.querySelector("#app");
const dialog = document.querySelector("#modal");
const editor = document.querySelector("#editor");
const state = {session:null, csrf:"", org:null, staff:[], customers:[], leads:[], visits:[],
  lead:null, generation:0, noticeTimer:null, saving:false};
const office = () => state.org?.role !== "FIELD";
const manager = () => ["OWNER","COORDINATOR"].includes(state.org?.role);
const owner = () => state.org?.role === "OWNER";
const closed = lead => ["LOST","WON"].includes(lead?.status);
const brand = '<div class="brand"><span class="brand-mark">S/</span>Studio.OS</div>';
const badge = (text,kind="") => `<span class="badge ${kind}">${h(human(text))}</span>`;
const button = (label,action,id="",style="secondary",extra="") => `<button type="button" class="${style}" data-action="${action}" data-id="${h(id)}" ${extra}>${h(label)}</button>`;
const empty = (title,text) => `<div class="empty"><h3>${h(title)}</h3><p>${h(text)}</p></div>`;
const field = (label,name,value="",type="text",options="") => `<label class="field">${h(label)}<input type="${type}" name="${name}" value="${h(value)}" ${options}></label>`;
const area = (label,name,value="",required=true) => `<label class="field">${h(label)}<textarea name="${name}" ${required?"required":""}>${h(value)}</textarea></label>`;
const note = text => `<div class="note">${h(text)}</div>`;
const staffOptions = selected => state.staff.map(s => `<option value="${s.id}" ${s.id===Number(selected)?"selected":""}>${h(s.name)} · ${h(human(s.role))}</option>`).join("");
const staffSelect = selected => `<label class="field">Assigned to<select name="assignee" required>${staffOptions(selected)}</select></label>`;
const staffName = id => state.staff.find(s=>s.id===id)?.name || (id===state.session.user.id ? state.session.user.name : "Staff member");
const customerName = id => state.customers.find(c=>c.id===id)?.name || "Customer";
const value = (form,name) => new FormData(form).get(name);
const jsonPost = (path,data,method="POST") => api(path,{method,body:JSON.stringify(data)});
const route = () => location.hash.replace(/^#/,"").split("/").filter(Boolean);
const go = path => { if (location.hash === "#"+path) render(); else location.hash = path; };
let modalSubmit = null;
let returnFocus = null;
let modalOrg = null;

async function api(path, options={}) {
  const orgID = state.org?.id;
  const response = await fetch(path, {credentials:"same-origin", cache:"no-store", ...options,
    headers:{"Accept":"application/json", ...(options.body?{"Content-Type":"application/json"}:{}),
      ...(orgID?{"X-Organization-ID":String(orgID)}:{}),
      ...(options.method && options.method!=="GET"?{"X-CSRFToken":state.csrf}:{}), ...options.headers}});
  let data;
  try { data = await response.json(); } catch { data = {detail:response.status===403 ?
    "Access could not be verified. Refresh the workspace and sign in again." : "The service returned an unexpected response."}; }
  if (orgID !== state.org?.id) throw new Error("Company changed. Open the record again.");
  if (!response.ok) {
    const error = new Error(errorText(data));
    error.status = response.status;
    if (response.status===409) error.message += "\nRefresh the record before submitting again.";
    throw error;
  }
  return data;
}

function notify(message,error=false) {
  const el = document.querySelector("#notice");
  clearTimeout(state.noticeTimer);
  el.textContent = message; el.className = "notice"+(error?" error":""); el.hidden=false;
  state.noticeTimer = setTimeout(()=>{el.hidden=true;},6500);
}

function closeModal(force=false) {
  if (state.saving && !force) return;
  if (dialog.open) dialog.close();
  modalSubmit=null;
  returnFocus?.focus?.();
}
function openModal(title,body,submit,label="Save") {
  returnFocus = document.activeElement;
  modalOrg = state.org?.id;
  document.querySelector("#modal-title").textContent=title;
  document.querySelector("#modal-context").textContent=state.org?.name || "STUDIO WORKSPACE";
  document.querySelector("#modal-body").innerHTML=`<div class="stack">${body}</div>`;
  document.querySelector("#submit-button").textContent=label;
  document.querySelector("#submit-button").hidden=false;
  editor.querySelector(".modal-footer [data-close]").textContent="Cancel";
  document.querySelector("#form-error").hidden=true;
  editor.reset();
  modalSubmit=submit;
  dialog.showModal();
}
editor.addEventListener("submit",async event=>{
  event.preventDefault();
  if (state.saving || !modalSubmit) return;
  if (modalOrg!==state.org?.id) { closeModal(); notify("Company changed. Open the record again.",true); return; }
  const submit=modalSubmit;
  state.saving=true;
  editor.querySelectorAll("button").forEach(b=>b.disabled=true);
  const errorEl=document.querySelector("#form-error");
  errorEl.hidden=true;
  try {
    await submit(editor);
    closeModal(true);
    notify("Saved.");
    await render();
  } catch(error) {
    errorEl.textContent=error.message; errorEl.hidden=false; errorEl.scrollIntoView?.({block:"nearest"});
    if (error.status===409) notify("This record changed. Close this form and refresh before editing.",true);
  } finally { state.saving=false; editor.querySelectorAll("button").forEach(b=>b.disabled=false); }
});
dialog.addEventListener("cancel",event=>{if(state.saving)event.preventDefault();});
dialog.addEventListener("click",event=>{
  const action=event.target.closest("[data-local]")?.dataset.local;
  if (event.target.closest("[data-close]")) closeModal();
  if (action==="add-measurement") addMeasurement();
  if (action==="add-line") addLine();
  if (action==="remove-item") event.target.closest(".item-editor").remove();
});

function loginScreen() {
  root.innerHTML=`<div class="login-layout"><section class="login-story">${brand}<div><p class="eyebrow">YOUR STUDIO, IN ORDER</p><h1>Less chasing.<br>More creating.</h1><p>Keep every inquiry, site visit and quotation moving—with a clear next step.</p><div class="rule"></div></div><p class="muted">A little structure. Room for better work.</p></section><section class="login-form-wrap"><form id="login" class="login-form"><p class="eyebrow">WELCOME BACK</p><h2>Open your studio.</h2><p class="muted">Sign in with your workspace account.</p><div class="stack">${field("Username","username","","text",'required autocomplete="username" maxlength="150"')}${field("Password","password","","password",'required autocomplete="current-password" maxlength="1024"')}<div id="login-error" class="form-error" role="alert" hidden></div><button class="primary" type="submit">Sign in →</button></div></form></section></div>`;
  root.setAttribute("aria-busy","false");
  root.querySelector("#login").addEventListener("submit",async event=>{
    event.preventDefault();
    const form=event.currentTarget, submit=form.querySelector("button"), err=form.querySelector("#login-error");
    submit.disabled=true; err.hidden=true;
    try {
      const data=await jsonPost("/api/session/login/",{username:value(form,"username"),password:value(form,"password")});
      form.reset(); setSession(data); await render();
    } catch(error) {err.textContent=error.message;err.hidden=false;submit.disabled=false;}
  });
}
function setSession(data) {
  state.session=data; state.csrf=data.csrf_token; state.lead=null;
  state.customers=[];state.leads=[];state.visits=[];state.staff=[];
  let saved;
  try {saved=sessionStorage.getItem("studio-org:"+data.user?.id);} catch {}
  state.org=data.organizations.find(org=>String(org.id)===saved)||data.organizations[0]||null;
}
function shell(active) {
  const nav=[["today","◷","Today"],...(office()?[["inquiries","▤","Inquiries"],["visits","□","Site visits"],["customers","○","Customers"]]:[["visits","□","My visits"]])];
  root.innerHTML=`<div class="shell"><aside class="sidebar">${brand}<div class="company"><label class="company-label" for="company">YOUR WORKSPACE</label><select id="company" class="company-select">${state.session.organizations.map(org=>`<option value="${org.id}" ${org.id===state.org.id?"selected":""}>${h(org.name)}</option>`).join("")}</select></div><nav class="nav" aria-label="Workspace">${nav.map(([path,icon,label])=>`<button data-nav="${path}" class="${active===path?"active":""}" ${active===path?'aria-current="page"':""}><span class="nav-symbol" aria-hidden="true">${icon}</span>${label}</button>`).join("")}</nav><div class="sidebar-foot"><strong>${h(state.session.user.name)}</strong><span class="role">${h(human(state.org.role))}</span>${button("Sign out","logout","","quiet")}</div></aside><div><header class="topbar"><span>${h(state.org.name)} / ${h(active==="inquiry"?"Inquiry":human(active))}</span><span>${h(formatDate(new Date().toISOString(),false))} · Nairobi time</span>${button("Refresh","refresh","","quiet")}</header><main id="main" tabindex="-1" aria-busy="true"><p class="muted">Loading your work…</p></main></div></div>`;
  root.setAttribute("aria-busy","false");
  root.querySelector("#company").addEventListener("change",event=>{
    state.org=state.session.organizations.find(org=>org.id===Number(event.target.value));
    state.lead=null;state.leads=[];state.customers=[];state.staff=[];state.visits=[];
    state.generation++;
    closeModal(true);
    try {sessionStorage.setItem("studio-org:"+state.session.user.id,state.org.id);} catch {}
    go("today");
  });
}
async function render() {
  const generation=++state.generation;
  if (!state.session?.authenticated) {loginScreen(); return;}
  if (!state.org) {
    root.innerHTML=`<div class="unavailable">${brand}<h1 class="detail-head">No workspace assigned.</h1><p class="prose">Your account has no active company membership. Ask your studio owner to add you.</p>${button("Sign out","logout")}</div>`;return;
  }
  const [page="today",id,tab="overview"]=route();
  const active=["today","inquiries","visits","customers","inquiry"].includes(page)?page:"today";
  shell(active==="inquiry"?"inquiries":active);
  const main=root.querySelector("#main");
  try {
    const paths=office()?["/api/customers/","/api/leads/","/api/staff/","/api/consultations/"]:["/api/consultations/"];
    const data=await Promise.all(paths.map(path=>api(path)));
    if(generation!==state.generation)return;
    if(office()) [state.customers,state.leads,state.staff,state.visits]=data; else state.visits=data[0];
    if(active==="today") {
      const actions=await api("/api/today/");
      if(generation!==state.generation)return;
      main.innerHTML=todayPage(actions);
    } else if(active==="inquiry"&&office()) {
      state.lead=await api("/api/leads/"+encodeURIComponent(id)+"/");
      if(generation!==state.generation)return;
      main.innerHTML=inquiryPage(state.lead,tab);
    } else if(active==="inquiries"&&office()) main.innerHTML=inquiriesPage();
    else if(active==="customers"&&office()) main.innerHTML=customersPage();
    else if(active==="visits") main.innerHTML=visitsPage();
    else main.innerHTML=empty("This area is unavailable","Use Today or your assigned site visits.");
    main.setAttribute("aria-busy","false");
  } catch(error) {
    if(generation!==state.generation)return;
    main.innerHTML=`<div class="card"><h2>We couldn’t load this work.</h2><p class="prose">${h(error.message)}</p><div class="actions">${button("Try again","refresh")}${button("Sign out","logout","","quiet")}</div></div>`;
    main.setAttribute("aria-busy","false");
  }
}
const pageHead=(eyebrow,title,description,action="")=>`<div class="page-head"><div><p class="eyebrow">${h(eyebrow)}</p><h1>${h(title)}</h1><p class="muted">${h(description)}</p></div>${action}</div>`;
function actionRow(action) {
  const overdue=action.due_at&&new Date(action.due_at)<new Date();
  return `<div class="row"><div class="row-main"><h3>${overdue?'<span class="dot" aria-hidden="true"></span>':""}${h(action.title)}</h3><p class="muted">${h(action.customer_name)} · ${h(formatDate(action.due_at))} · ${h(staffName(action.assignee))}</p></div>${button(action.consultation||action.origin_key?"Open work":"Record outcome","task",action.id)}</div>`;
}
function todayPage(actions) {
  const overdue=actions.filter(a=>a.due_at&&new Date(a.due_at)<new Date()).length;
  const review=actions.filter(a=>a.origin_key?.startsWith("quote:")).length;
  const visits=state.visits.filter(v=>v.status==="CONFIRMED"&&new Date(v.ends_at)>=new Date());
  return pageHead("THE DAILY VIEW","Good work starts here.","Your follow-ups, site visits and decisions, in one place.",office()?button("+ New inquiry","new-inquiry","","primary"):"")+
    `<div class="stats"><div class="stat"><span>OPEN TODAY</span><strong>${actions.length}</strong><span>actions to move forward</span></div><div class="stat"><span>NEEDS ATTENTION</span><strong>${overdue}</strong><span>past their planned time</span></div><div class="stat"><span>OWNER REVIEW</span><strong>${review}</strong><span>drafts awaiting a decision</span></div></div><div class="grid"><section class="panel"><div class="panel-head"><h3>Your action list</h3><span class="pill-count">${actions.length} open</span></div>${actions.length?actions.map(actionRow).join(""):empty("A little breathing room.","No open actions are due today. Future work stays with its inquiry.")}</section><aside><section class="panel"><div class="panel-head"><h3>Coming up on site</h3></div>${visits.slice(0,4).map(visitRow).join("")||empty("No confirmed visits","Confirmed appointments will appear here.")}</section><div class="note" style="margin-top:20px">Changes to scope or prices stay in history. Owner review is an internal decision; it sends nothing to the customer.</div></aside></div>`;
}
function inquiriesPage() {
  return pageHead("CUSTOMER WORK","Every inquiry has a next step.","Keep the conversation, visit and estimate together.",button("+ New inquiry","new-inquiry","","primary"))+
    `<div class="filterbar"><input type="search" id="inquiry-search" aria-label="Search inquiries" placeholder="Find a customer or brief…"></div><section class="panel"><div class="panel-head"><h3>Inquiry register</h3><span class="pill-count">${state.leads.length}</span></div><div id="inquiry-list">${inquiryRows(state.leads)}</div></section>`;
}
function inquiryRows(leads) {
  return leads.map(lead=>`<div class="row"><div class="row-main"><button class="row-title" data-action="open-inquiry" data-id="${lead.id}">${h(customerName(lead.customer))}</button><p class="muted">${h(lead.brief||"Scope still to be discussed")}</p></div><div class="actions">${badge(lead.status)}${button("Open →","open-inquiry",lead.id,"quiet")}</div></div>`).join("")||empty("No matching inquiries","Create an inquiry to record a customer’s request and queue the first response.");
}
function customersPage() {
  return pageHead("YOUR DIRECTORY","People behind the projects.","Customer contacts stay connected to their inquiry history.",button("+ Add customer","new-customer","","primary"))+
    `<section class="panel"><div class="panel-head"><h3>Customers</h3></div>${state.customers.map(c=>`<div class="row"><div><h3>${h(c.name)}</h3><p class="muted">${h([c.email,c.phone].filter(Boolean).join(" · ")||"No contact details recorded")}</p></div>${button("New inquiry","customer-inquiry",c.id)}</div>`).join("")||empty("Start with a customer","Add the person you’re speaking to. You can record their inquiry next.")}</section>`;
}
function visitRow(visit) {
  return `<div class="row"><div class="row-main"><button class="row-title" data-action="visit" data-id="${visit.id}">${h(visit.location)}</button><p class="muted">${h(formatDate(visit.starts_at))} · ${h(staffName(visit.assignee))}</p></div>${badge(visit.status,visit.status==="CANCELLED"?"gray":"")}</div>`;
}
function visitsPage() {
  return pageHead("OUT OF THE STUDIO",office()?"Site visits":"Your site visits","Proposed visits reserve no time. Confirmation checks for overlapping bookings.")+
    `<section class="panel"><div class="panel-head"><h3>Visit schedule</h3></div>${state.visits.map(visitRow).join("")||empty("No visits yet",office()?"Open a qualified inquiry to propose its first site visit.":"Your assigned visits will appear here.")}</section>`;
}
function inquiryPage(lead,tab) {
  const customer=state.customers.find(c=>c.id===lead.customer);
  const tabs=[["overview","Overview"],["visits","Site visits"],["assessments","Assessments"],["quotes","Quotations"],["history","History"]];
  const selected=tabs.some(([key])=>key===tab)?tab:"overview";
  let content="";
  if(selected==="overview") content=`<div class="grid"><div><section class="card"><p class="eyebrow">THE REQUEST</p><p class="prose">${h(lead.brief||"No brief recorded yet.")}</p><p class="muted">${h([customer?.email,customer?.phone].filter(Boolean).join(" · ")||"Contact details not recorded")}</p></section><section class="panel"><div class="panel-head"><h3>Next actions</h3>${!closed(lead)?button("+ Plan action","plan-action",lead.id):""}</div>${lead.actions.filter(a=>!a.done&&!a.cancelled).map(actionRow).join("")||empty("Nothing pending","Record the next action when you know what needs to happen.")}</section></div><section class="card"><p class="eyebrow">WHERE THINGS STAND</p><h2>${h(human(lead.status))}</h2><p class="prose">Move the inquiry forward when the conversation or site work supports it. Every stage change keeps a note.</p>${!closed(lead)?button("Update inquiry stage","lead-stage",lead.id):""}<p class="muted" style="margin-top:20px">Opened ${h(formatDate(lead.created_at))}</p></section></div>`;
  if(selected==="visits") content=`${!closed(lead)&&["QUALIFIED","CONSULTATION_BOOKED"].includes(lead.status)?`<div class="actions" style="margin-bottom:20px">${button("+ Propose site visit","new-visit",lead.id,"primary")}</div>`:""}${lead.consultations.map(v=>`<section class="card"><div class="card-head"><div><h3>${h(v.location)}</h3><p class="muted">${h(formatDate(v.starts_at))} — ${h(formatDate(v.ends_at))}</p></div>${badge(v.status)}</div><p class="muted">Assigned to ${h(staffName(v.assignee))}</p>${v.outcome?`<p class="prose">${h(v.outcome)}</p>`:""}<div class="actions">${button("Open visit","visit",v.id)}${v.status==="COMPLETED"&&!lead.assessments.some(a=>a.consultation===v.id)&&!closed(lead)?button("Record assessment","new-assessment",v.id,"primary"):""}</div></section>`).join("")||empty("Ready for a site visit?","Qualify the inquiry first, then propose a time and assign staff.")}`;
  if(selected==="assessments") content=lead.assessments.map(a=>`<section class="card"><div class="card-head"><div><h3>Site assessment #${a.id}</h3><p class="muted">Visit #${a.consultation} · ${h(formatDate(a.created_at))}</p></div>${badge(a.status)}</div><p class="prose">${h(a.scope||"Scope not yet recorded")}</p>${a.missing_information.length?`<div class="note warn">Missing: ${h(a.missing_information.join(", "))}</div>`:""}${a.provisional_reason?note("Preliminary estimate authorized: "+a.provisional_reason):""}<div class="actions">${button("Open assessment","assessment",a.id)}${a.status==="READY_FOR_ESTIMATE"&&!lead.quotes.some(q=>q.assessment===a.id)&&!closed(lead)?button("Draft quotation","new-quote",a.id,"primary"):""}</div></section>`).join("")||empty("No assessment recorded","Complete the site visit, then record scope and measurements.");
  if(selected==="quotes") content=lead.quotes.map(q=>`<section class="card"><div class="card-head"><div><h3>Quotation #${q.id}</h3><p class="muted">Revision ${q.current_revision.number} · ${h(formatDate(q.created_at))}</p></div>${badge(q.status)}</div><h2>${h(money(q.current_revision.total,q.currency))}</h2>${!q.source_current?'<div class="note warn" style="margin-top:15px">Assessment information has changed. Prepare a new revision before review.</div>':""}<div class="actions">${button("Open quotation","quote",q.id)}</div></section>`).join("")||empty("No quotation yet","A ready assessment provides the source for your first draft.");
  if(selected==="history") content=`<div class="timeline">${[...lead.activities].reverse().map(a=>`<article class="event"><time>${h(formatDate(a.created_at))}</time><h3>${h(human(a.kind))}</h3><p>${h(a.details.note||"Recorded in your workspace")}</p></article>`).join("")||empty("History starts here","Changes and recorded outcomes will appear as work progresses.")}</div>`;
  return button("← All inquiries","back-inquiries","","quiet")+pageHead("INQUIRY / "+lead.id,customer?.name||"Customer","One record, from first conversation to reviewed quotation.")+
    `<div class="detail-meta">${badge(lead.status)}<span class="muted">Inquiry #${lead.id}</span></div><div class="tabs" role="navigation" aria-label="Inquiry sections">${tabs.map(([key,label])=>`<button data-action="tab" data-id="${key}" class="${key===selected?"active":""}" ${key===selected?'aria-current="page"':""}>${h(label)}</button>`).join("")}</div>${content}`;
}

root.addEventListener("input",event=>{
  if(event.target.id==="inquiry-search") {
    const query=event.target.value.toLowerCase();
    document.querySelector("#inquiry-list").innerHTML=inquiryRows(state.leads.filter(l=>
      (customerName(l.customer)+" "+l.brief).toLowerCase().includes(query)));
  }
});
root.addEventListener("click",event=>{
  const nav=event.target.closest("[data-nav]"); if(nav)go(nav.dataset.nav);
});
async function getLead(id) { return api("/api/leads/"+id+"/"); }
async function getAction(id) {
  const actions=await api("/api/today/");
  let action=actions.find(a=>a.id===Number(id))||state.lead?.actions.find(a=>a.id===Number(id));
  if(!action)throw new Error("This action has changed or is no longer due. Refresh your work.");
  return action;
}
async function handleAction(action,id) {
  if(action==="refresh")return state.session?render():start();
  if(action==="logout") {
    const data=await jsonPost("/api/session/logout/",{});
    state.generation++; closeModal(true); setSession(data); return render();
  }
  if(action==="open-inquiry")return go("inquiry/"+id+"/overview");
  if(action==="back-inquiries")return go("inquiries");
  if(action==="tab")return go("inquiry/"+state.lead.id+"/"+id);
  if(action==="new-customer")return newCustomer();
  if(action==="new-inquiry")return newInquiry();
  if(action==="customer-inquiry")return newInquiry(Number(id));
  if(action==="lead-stage")return stageModal(await getLead(id));
  if(action==="plan-action")return planAction(await getLead(id));
  if(action==="new-visit")return scheduleVisit(Number(id));
  if(action==="visit")return visitModal(state.visits.find(v=>v.id===Number(id)));
  if(action==="new-assessment")return assessmentEditor(null,Number(id));
  if(action==="assessment")return assessmentModal(await api("/api/assessments/"+id+"/"));
  if(action==="new-quote")return quoteEditor(null,await api("/api/assessments/"+id+"/"));
  if(action==="quote")return quoteModal(await api("/api/quotes/"+id+"/"));
  if(action==="task") {
    const task=await getAction(id), target=routeForAction(task,!office());
    if(target.type==="action")return completeAction(task);
    if(target.type==="visit")return visitModal(state.visits.find(v=>v.id===target.id));
    if(target.type==="assessment")return assessmentModal(await api("/api/assessments/"+target.id+"/"));
    if(target.type==="quote")return quoteModal(await api("/api/quotes/"+target.id+"/"));
  }
}
root.addEventListener("click",async event=>{
  const el=event.target.closest("[data-action]"); if(!el)return;
  el.disabled=true;
  try {await handleAction(el.dataset.action,el.dataset.id);} catch(error){notify(error.message,true);}
  finally {el.disabled=false;}
});

function newCustomer() {
  openModal("Add a customer",field("Customer name","name","","text","required maxlength=180")+
    field("Email (optional)","email","","email")+field("Phone (optional)","phone","","tel",'maxlength="40"'),
    form=>jsonPost("/api/customers/",{name:value(form,"name"),email:value(form,"email"),phone:value(form,"phone")}),"Add customer");
}
function newInquiry(selected) {
  if(!state.customers.length) {
    notify("Add a customer first, then record their inquiry.");
    return newCustomer();
  }
  openModal("Record an inquiry",`<label class="field">Customer<select name="customer" required>${state.customers.map(c=>`<option value="${c.id}" ${c.id===selected?"selected":""}>${h(c.name)}</option>`).join("")}</select></label>`+
    area("What are they looking for?","brief","",false)+note("Saving creates a response action. No message is sent."),
    async form=>{await jsonPost("/api/leads/",{customer:Number(value(form,"customer")),brief:value(form,"brief")});},"Record inquiry");
}
function stageModal(lead) {
  const targets=leadTargets(lead.status);
  if(!targets.length)throw new Error("This inquiry has no available stage changes.");
  openModal("Update inquiry stage",note("Current stage: "+human(lead.status))+
    `<label class="field">Move to<select name="status">${targets.map(s=>`<option value="${s}">${h(human(s))}</option>`).join("")}</select></label>`+
    area("What supports this change?","note")+note("Marking an inquiry lost cancels its open work and revokes pending quotation approval."),
    form=>jsonPost("/api/leads/"+lead.id+"/transition/",{expected_version:lead.version,status:value(form,"status"),note:value(form,"note")}));
}
function planAction(lead) {
  openModal("Plan the next action",field("What needs to happen?","title","","text","required maxlength=180")+
    field("Planned time · Nairobi (optional)","due_at","","datetime-local")+
    (manager()?staffSelect(state.session.user.id):note("This action will be assigned to you.")),
    form=>jsonPost("/api/leads/"+lead.id+"/actions/",{title:value(form,"title"),
      due_at:value(form,"due_at")?fromNairobiInput(value(form,"due_at")):null,
      assignee:manager()?Number(value(form,"assignee")):state.session.user.id}));
}
function completeAction(task) {
  openModal(task.title,area("What happened?","note")+
    field("Follow-up action (optional)","follow_up_title","","text","maxlength=180")+
    field("Follow-up time · Nairobi (optional)","follow_up_due_at","","datetime-local")+
    (manager()?button("Change assignment or planned time","",task.id,"quiet",'id="reschedule-action"'):""),
    form=>{
      const payload={expected_version:task.version,note:value(form,"note")};
      if(value(form,"follow_up_title")||value(form,"follow_up_due_at")) {
        payload.follow_up_title=value(form,"follow_up_title");
        payload.follow_up_due_at=fromNairobiInput(value(form,"follow_up_due_at"));
      }
      return jsonPost("/api/actions/"+task.id+"/complete/",payload);
    },"Complete action");
  document.querySelector("#reschedule-action")?.addEventListener("click",()=>{
    openModal("Change planned action",field("Action","title",task.title,"text","required maxlength=180")+
      field("Planned time · Nairobi (optional)","due_at",nairobiInput(task.due_at),"datetime-local")+
      staffSelect(task.assignee)+area("Reason for the change","note"),
      form=>jsonPost("/api/actions/"+task.id+"/",{expected_version:task.version,title:value(form,"title"),
        due_at:value(form,"due_at")?fromNairobiInput(value(form,"due_at")):null,
        assignee:Number(value(form,"assignee")),note:value(form,"note")},"PATCH"));
  });
}
function scheduleVisit(leadId,visit=null) {
  openModal(visit?"Reschedule site visit":"Propose a site visit",
    note("Times are entered in Nairobi time. Confirmation checks staff availability.")+
    field("Start · Nairobi","starts_at",nairobiInput(visit?.starts_at),"datetime-local","required")+
    field("End · Nairobi","ends_at",nairobiInput(visit?.ends_at),"datetime-local","required")+
    field("Site location","location",visit?.location||"","text","required maxlength=300")+
    (manager()?staffSelect(visit?.assignee||state.session.user.id):note("This visit is assigned to you."))+
    (visit?area("Why is the visit changing?","note"):""),
    form=>{
      const payload={starts_at:fromNairobiInput(value(form,"starts_at")),ends_at:fromNairobiInput(value(form,"ends_at")),
        location:value(form,"location"),assignee:manager()?Number(value(form,"assignee")):state.session.user.id};
      return visit?jsonPost("/api/consultations/"+visit.id+"/command/",{...payload,
        expected_version:visit.version,command:"reschedule",note:value(form,"note")}):
        jsonPost("/api/leads/"+leadId+"/consultations/",payload);
    },visit?"Save & request confirmation":"Save proposal");
}
async function visitModal(visit) {
  if(!visit)throw new Error("Visit unavailable. Refresh your schedule.");
  const commands=[];
  if(office()&&["PROPOSED","RESCHEDULED"].includes(visit.status))commands.push(["confirm","Confirm visit"]);
  if(office()&&["PROPOSED","CONFIRMED","RESCHEDULED"].includes(visit.status))commands.push(["cancel","Cancel visit"]);
  if(visit.status==="CONFIRMED")commands.push(["complete","Visit completed"],["no_show","Customer did not attend"]);
  const lead=office()?await getLead(visit.lead):null;
  const hasAssessment=lead?.assessments.some(a=>a.consultation===visit.id);
  if(!commands.length) {
    readOnly("Site visit",note(human(visit.status))+
      `<h3>${h(visit.location)}</h3><p class="muted">${h(formatDate(visit.starts_at))}</p><p class="prose">${h(visit.outcome||"No outcome notes recorded")}</p>`+
      (office()&&visit.status==="COMPLETED"&&!hasAssessment&&!closed(lead)?'<button type="button" class="primary" id="visit-assessment">Record assessment</button>':"")+
      (office()?'<button type="button" class="quiet" id="terminal-visit-lead">Open inquiry →</button>':""),
      null);
    on("visit-assessment",()=>assessmentEditor(null,visit.id));
    on("terminal-visit-lead",()=>{closeModal();go("inquiry/"+visit.lead+"/visits");});
    return;
  }
  openModal("Site visit",`<div>${badge(visit.status)}<h3 style="margin-top:15px">${h(visit.location)}</h3><p class="muted">${h(formatDate(visit.starts_at))} — ${h(formatDate(visit.ends_at))}</p></div>`+
    `<label class="field">Record a decision<select name="command">${commands.map(([key,label])=>`<option value="${key}">${h(label)}</option>`).join("")}</select></label>`+
    area("Notes / visit outcome","note")+
    (office()?button("Open inquiry","",visit.lead,"quiet",'id="visit-lead"'):"")+
    (office()&&(manager()||visit.assignee===state.session.user.id)&&["PROPOSED","CONFIRMED","RESCHEDULED"].includes(visit.status)?'<button type="button" class="secondary" id="reschedule-visit">Change date or assignment</button>':""),
    form=>jsonPost("/api/consultations/"+visit.id+"/command/",{expected_version:visit.version,
      command:value(form,"command"),note:value(form,"note")}),"Record decision");
  document.querySelector("#reschedule-visit")?.addEventListener("click",()=>scheduleVisit(visit.lead,visit));
  document.querySelector("#visit-lead")?.addEventListener("click",()=>{closeModal();go("inquiry/"+visit.lead+"/visits");});
}

function readOnly(title,body) {
  openModal(title,body,null);
  document.querySelector("#submit-button").hidden=true;
  editor.querySelector(".modal-footer [data-close]").textContent="Close";
}
function on(id,handler) {
  document.getElementById(id)?.addEventListener("click",async event=>{
    const el=event.currentTarget;
    el.disabled=true;
    try {await handler();}catch(error){notify(error.message,true);}finally{el.disabled=false;}
  });
}
function addMeasurement(item={label:"",value:null,unit:"m",required:true}) {
  const container=document.querySelector("#measurement-rows");
  const row=document.createElement("div");row.className="item-editor measurement-row";
  row.innerHTML=`<div class="line-fields">${field("Dimension / item","measurement-label",item.label,"text","required maxlength=180")}${field("Value (leave blank if unknown)","measurement-value",item.value??"","number",'min="0.001" step="0.001"')}<label class="field">Unit<select name="measurement-unit">${["mm","cm","m","m2","count"].map(unit=>`<option value="${unit}" ${unit===item.unit?"selected":""}>${unit==="m2"?"m²":unit}</option>`).join("")}</select></label></div><div class="actions"><label class="checkbox"><input type="checkbox" name="measurement-required" ${item.required?"checked":""}>Required for estimate</label><button type="button" class="quiet" data-local="remove-item">Remove dimension</button></div>`;
  container.append(row);
}
function measurementsFromForm() {
  return [...document.querySelectorAll(".measurement-row")].map(row=>({
    label:row.querySelector('[name="measurement-label"]').value,
    value:row.querySelector('[name="measurement-value"]').value||null,
    unit:row.querySelector('[name="measurement-unit"]').value,
    required:row.querySelector('[name="measurement-required"]').checked,
  }));
}
function assessmentEditor(assessment,visitID) {
  openModal(assessment?"Edit site observations":"Record site assessment",
    area("Proposed scope","scope",assessment?.scope||"",false)+
    area("Site notes / constraints","notes",assessment?.notes||"",false)+
    note("Leave a measurement blank if it is unknown. Required dimensions must be recorded before estimate readiness, unless an owner authorizes a preliminary estimate.")+
    '<div><p class="eyebrow">MEASUREMENTS</p><div id="measurement-rows"></div><button type="button" class="secondary" data-local="add-measurement">+ Add dimension</button></div>'+
    (assessment?area("Reason for updating observations","note"):""),
    form=>{
      const payload={scope:value(form,"scope"),notes:value(form,"notes"),measurements:measurementsFromForm()};
      return assessment?jsonPost("/api/assessments/"+assessment.id+"/",{...payload,
        expected_version:assessment.version,note:value(form,"note")},"PATCH"):
        jsonPost("/api/consultations/"+visitID+"/assessment/",payload);
    },assessment?"Save observations":"Save assessment draft");
  (assessment?.measurements.length?assessment.measurements:[{label:"",value:null,unit:"m",required:true}]).forEach(addMeasurement);
}
async function assessmentModal(assessment) {
  const visit=state.visits.find(v=>v.id===assessment.consultation);
  const lead=visit?await getLead(visit.lead):null;
  const quote=lead?.quotes.find(q=>q.assessment===assessment.id);
  const editable=lead&&!closed(lead);
  readOnly("Site assessment #"+assessment.id,
    `<div>${badge(assessment.status)}<p class="prose">${h(assessment.scope||"Scope not yet recorded")}</p><p class="muted">${h(assessment.notes)}</p></div>`+
    (assessment.missing_information.length?`<div class="note warn">Missing: ${h(assessment.missing_information.join(", "))}</div>`:"")+
    (assessment.provisional_reason?note("Owner authorized a preliminary estimate: "+assessment.provisional_reason):"")+
    `<div class="table-wrap"><table><thead><tr><th>Dimension</th><th>Value</th><th>Required</th></tr></thead><tbody>${assessment.measurements.map(m=>`<tr><td>${h(m.label)}</td><td>${h(m.value??"Unknown")} ${h(m.unit)}</td><td>${m.required?"Yes":"No"}</td></tr>`).join("")}</tbody></table></div><div class="actions">`+
    (editable&&assessment.status!=="READY_FOR_ESTIMATE"?'<button type="button" class="secondary" id="edit-assessment">Edit observations</button><button type="button" class="primary" id="ready-assessment">Review readiness</button>':"")+
    (editable&&assessment.status==="READY_FOR_ESTIMATE"?'<button type="button" class="secondary" id="reopen-assessment">Reopen for correction</button>'+(!quote?'<button type="button" class="primary" id="draft-quote">Draft quotation</button>':""):"")+
    (quote?'<button type="button" class="primary" id="open-assessment-quote">Open quotation</button>':"")+
    (lead?'<button type="button" class="quiet" id="assessment-inquiry">Open inquiry →</button>':"")+"</div>");
  on("edit-assessment",()=>assessmentEditor(assessment));
  on("ready-assessment",()=>assessmentCommand(assessment,"ready"));
  on("reopen-assessment",()=>assessmentCommand(assessment,"reopen"));
  on("draft-quote",()=>quoteEditor(null,assessment));
  on("open-assessment-quote",async()=>quoteModal(await api("/api/quotes/"+quote.id+"/")));
  on("assessment-inquiry",()=>{closeModal();go("inquiry/"+lead.id+"/assessments");});
}
function assessmentCommand(assessment,command) {
  openModal(command==="ready"?"Review estimate readiness":"Reopen site assessment",
    (command==="reopen"?note("Reopening revokes quotation approval. The updated assessment will need a new quotation revision before review."):
      assessment.missing_information.length?`<div class="note warn">Missing: ${h(assessment.missing_information.join(", "))}. ${owner()?"An owner can record why a preliminary estimate is appropriate.":"Record the dimensions before marking ready."}</div>`:note("The recorded required dimensions are complete. Check scope and observations before continuing."))+
    area(command==="ready"?"What did you check?":"Why are you reopening it?","note")+
    (command==="ready"&&owner()?area("Preliminary-estimate reason (optional)","provisional_reason","",false):""),
    form=>{
      const payload={expected_version:assessment.version,command,note:value(form,"note")};
      if(value(form,"provisional_reason"))payload.provisional_reason=value(form,"provisional_reason");
      return jsonPost("/api/assessments/"+assessment.id+"/command/",payload);
    },command==="ready"?"Mark ready for estimate":"Reopen assessment");
}
function addLine(item={description:"",quantity:"1.000",unit_price:""}) {
  const row=document.createElement("div");row.className="item-editor quote-line";
  row.innerHTML=`<div class="line-fields">${field("Work / material","line-description",item.description,"text","required maxlength=300")}${field("Quantity","line-quantity",item.quantity,"number",'required min="0.001" step="0.001"')}${field("Unit price","line-price",item.unit_price,"number",'required min="0" step="0.01"')}</div><button type="button" class="quiet" data-local="remove-item">Remove line</button>`;
  document.querySelector("#quote-lines").append(row);
}
function quoteEditor(quote,assessment) {
  const revision=quote?.current_revision;
  openModal(quote?"Create quotation revision":"Draft a quotation",
    note("Currency: "+(quote?.currency||"company currency")+". Totals will be calculated by the server when you save. This is an internal draft; nothing is sent.")+
    `<div><p class="eyebrow">FROM THE ASSESSMENT</p><p class="prose">${h(assessment.scope)}</p></div>`+
    (assessment.provisional_reason?note("Preliminary estimate: "+assessment.provisional_reason):"")+
    '<div><p class="eyebrow">ESTIMATE LINES</p><div id="quote-lines"></div><button type="button" class="secondary" data-local="add-line">+ Add line</button></div>'+
    '<div class="split">'+field("Discount","discount",revision?.discount||"0.00","number",'required min="0" step="0.01"')+
    field("Tax factor (0–1)","tax_rate",revision?.tax_rate||"0","number",'required min="0" max="1" step="0.000001"')+"</div>"+
    '<p class="muted">Enter the factor your studio uses, for example 0.10 for 10%. No tax rate is assumed.</p>'+
    (quote?area("What changed in this revision?","note"):""),
    form=>{
      const items=[...document.querySelectorAll(".quote-line")].map(row=>({
        description:row.querySelector('[name="line-description"]').value,
        quantity:row.querySelector('[name="line-quantity"]').value,
        unit_price:row.querySelector('[name="line-price"]').value,
      }));
      if(!items.length)throw new Error("Add at least one estimate line.");
      const payload={expected_assessment_version:assessment.version,items,
        discount:value(form,"discount"),tax_rate:value(form,"tax_rate")};
      return quote?jsonPost("/api/quotes/"+quote.id+"/revisions/",{...payload,
        expected_version:quote.version,note:value(form,"note")}):
        jsonPost("/api/assessments/"+assessment.id+"/quote/",payload);
    },quote?"Save new revision":"Save quotation draft");
  (revision?.items||[{description:"",quantity:"1.000",unit_price:""}]).forEach(addLine);
}
function revisionContent(revision) {
  return (revision.provisional_reason_snapshot?note("Preliminary estimate: "+revision.provisional_reason_snapshot):"")+
    `<p class="prose">${h(revision.scope_snapshot)}</p><p class="muted">${h(revision.notes_snapshot)}</p><div class="table-wrap"><table><thead><tr><th>Description</th><th>Qty</th><th>Unit price</th><th>Amount</th></tr></thead><tbody>${revision.items.map(item=>`<tr><td>${h(item.description)}</td><td>${h(item.quantity)}</td><td>${h(money(item.unit_price,revision.currency))}</td><td>${h(money(item.amount,revision.currency))}</td></tr>`).join("")}</tbody></table></div><div class="totals"><div><span>Subtotal</span><span>${h(money(revision.subtotal,revision.currency))}</span></div><div><span>Discount</span><span>${h(money(revision.discount,revision.currency))}</span></div><div><span>Tax (factor ${h(revision.tax_rate)})</span><span>${h(money(revision.tax,revision.currency))}</span></div><div class="grand"><span>Total</span><span>${h(money(revision.total,revision.currency))}</span></div></div>`;
}
async function quoteModal(quote) {
  const assessment=await api("/api/assessments/"+quote.assessment+"/");
  const visit=state.visits.find(v=>v.id===assessment.consultation);
  const lead=visit?await getLead(visit.lead):null;
  const editable=lead&&!closed(lead);
  readOnly("Quotation #"+quote.id,
    `<div class="card-head"><div>${badge(quote.status)}<p class="muted" style="margin-top:12px">Revision ${quote.current_revision.number} · ${h(formatDate(quote.current_revision.created_at))}</p></div></div>`+
    (!quote.source_current?'<div class="note warn">The source assessment has changed or is not ready. Review it and save a new quotation revision before submitting.</div>':"")+
    revisionContent(quote.current_revision)+
    `<div class="actions">${editable&&assessment.status==="READY_FOR_ESTIMATE"?'<button type="button" class="secondary" id="revise-quote">New revision</button>':""}${editable&&quote.status==="DRAFT"&&quote.source_current?'<button type="button" class="primary" id="submit-quote">Submit for owner review</button>':""}${editable&&quote.status==="READY_FOR_REVIEW"&&owner()?'<button type="button" class="primary" id="approve-quote">Approve sharing internally</button>':""}${editable&&["READY_FOR_REVIEW","APPROVED_TO_SHARE"].includes(quote.status)?'<button type="button" class="secondary" id="withdraw-quote">Return to draft</button>':""}<button type="button" class="quiet" id="quote-source">Open source assessment →</button></div>`+
    note("Internal record only. Approval sends nothing and does not record customer acceptance.")+
    `<details><summary>Revision history (${quote.revisions.length})</summary>${quote.revisions.map(revision=>`<section class="card" style="margin-top:16px"><p class="eyebrow">REVISION ${revision.number} · ${h(formatDate(revision.created_at))}</p>${revisionContent(revision)}</section>`).join("")}</details>`);
  on("revise-quote",()=>quoteEditor(quote,assessment));
  on("submit-quote",()=>reviewQuote(quote,"submit"));
  on("approve-quote",()=>reviewQuote(quote,"approve"));
  on("withdraw-quote",()=>reviewQuote(quote,"return_to_draft"));
  on("quote-source",()=>assessmentModal(assessment));
}
function reviewQuote(quote,command) {
  const titles={submit:"Submit for owner review",approve:"Record owner approval",return_to_draft:"Return quotation to draft"};
  openModal(titles[command],note("Revision "+quote.current_revision.number+" · "+money(quote.current_revision.total,quote.currency))+
    area(command==="approve"?"What did you check before approval?":"Review note","note")+
    note("This records an internal decision. No customer message or acceptance is created."),
    form=>jsonPost("/api/quotes/"+quote.id+"/review/",{expected_version:quote.version,command,note:value(form,"note")}),
    command==="approve"?"Record internal approval":"Save decision");
}

window.addEventListener("hashchange",()=>{
  if(state.saving) return;
  closeModal(true);render();
});
async function start() {
  try {
    setSession(await api("/api/session/"));
    await render();
  }catch(error){
    root.innerHTML=`<div class="unavailable">${brand}<h1 class="detail-head">Workspace unavailable.</h1><p class="prose">${h(error.message)}</p>${button("Try again","refresh")}</div>`;
  }
}
start();
