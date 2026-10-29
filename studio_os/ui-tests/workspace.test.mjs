import {test} from "node:test";
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import {JSDOM} from "jsdom";
import * as utils from "../operations/static/studio_os/ui-utils.mjs";

const html=(await readFile(new URL("../operations/templates/studio_os/workspace.html",import.meta.url),"utf8"))
  .replace(/{%[\s\S]*?%}/g,"");
const source=(await readFile(new URL("../operations/static/studio_os/workspace.mjs",import.meta.url),"utf8"))
  .replace(/^import[\s\S]*?from "\.\/ui-utils\.mjs";/,
    "const {escapeHTML:h,human,formatDate,money,errorText,nairobiInput,fromNairobiInput,leadTargets,routeForAction}=window.testUtils;");
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function waitFor(check,message="Expected interface state") {
  for(let i=0;i<80;i++){if(check())return;await sleep(5);}
  assert.ok(check(),message);
}
function baseData(role="OWNER") {
  const assessment={id:30,consultation:20,scope:"Paint lounge",notes:"Protect floor",
    measurements:[{label:"Length",value:"4.200",unit:"m",required:true}],
    status:"READY_FOR_ESTIMATE",version:2,missing_information:[],provisional_reason:"",created_at:"2026-10-19T12:00:00Z"};
  const revision={id:50,number:1,assessment_version:2,scope_snapshot:"Paint lounge",notes_snapshot:"Protect floor",
    measurements_snapshot:assessment.measurements,provisional_reason_snapshot:"",currency:"KES",
    items:[{description:"Paint",quantity:"2.000",unit_price:"1000.00",amount:"2000.00"}],
    subtotal:"2000.00",discount:"0.00",tax_rate:"0.000000",tax:"0.00",total:"2000.00",created_at:"2026-10-19T12:00:00Z"};
  const quote={id:40,assessment:30,lead:10,customer_name:"Amina",currency:"KES",status:"READY_FOR_REVIEW",version:2,
    source_current:true,current_revision:revision,revisions:[revision],created_at:"2026-10-19T12:00:00Z"};
  const visit={id:20,lead:10,assignee:1,location:"Lounge site",starts_at:"2027-01-02T10:00:00+03:00",
    ends_at:"2027-01-02T11:00:00+03:00",status:"COMPLETED",version:3,outcome:"Measured site"};
  const lead={id:10,customer:5,brief:"Lounge renovation",status:"NEW",version:1,
    created_at:"2026-10-19T12:00:00Z",actions:[],consultations:[visit],assessments:[assessment],quotes:[quote],activities:[]};
  return {authenticated:true,csrf_token:"csrf-local-test",user:{id:1,name:"Yusuf"},
    organizations:[{id:1,name:"Nuru Interiors",role},{id:2,name:"Second studio",role:"FIELD"}],
    customers:[{id:5,name:"Amina",email:"amina@example.test",phone:""}],
    staff:[{id:1,name:"Yusuf",role}],leads:[lead],visits:[visit],actions:[],assessment,quote,lead};
}
async function harness(t,{data=baseData(),authenticated=true,hash="today",handler=null}={}) {
  const dom=new JSDOM(html,{url:"http://localhost/#"+hash,runScripts:"outside-only",pretendToBeVisual:true});
  const w=dom.window,calls=[];
  t.after(()=>dom.window.close());
  w.testUtils=utils;
  w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};
  w.HTMLDialogElement.prototype.close=function(){this.open=false;};
  w.HTMLElement.prototype.scrollIntoView=function(){};
  let signedIn=authenticated;
  const session=()=>({authenticated:signedIn,csrf_token:data.csrf_token,user:signedIn?data.user:null,
    organizations:signedIn?data.organizations:[]});
  w.fetch=async(path,options={})=>{
    const call={path,options,payload:options.body?JSON.parse(options.body):null};
    calls.push(call);
    let result;
    if(handler)result=await handler(call,data);
    if(!result) {
      if(path==="/api/session/")result={data:session()};
      else if(path==="/api/session/login/"){signedIn=true;result={data:session()};}
      else if(path==="/api/session/logout/"){signedIn=false;result={data:session()};}
      else if(path==="/api/customers/")result={data:options.method?{id:6,...call.payload}:data.customers};
      else if(path==="/api/leads/")result={data:options.method?{id:11,...call.payload}:data.leads};
      else if(path==="/api/staff/")result={data:data.staff};
      else if(path==="/api/quotes/")result={data:data.quotes||[data.quote]};
      else if(path==="/api/team/")result={data:[{id:70,user_id:1,username:"owner",name:"Yusuf",role:"OWNER",active:true,account_active:true,version:1,open_actions:0}]};
      else if(path==="/api/consultations/")result={data:data.visits};
      else if(path==="/api/today/")result={data:options.headers["X-Organization-ID"]==="2"?[]:data.actions};
      else if(path==="/api/leads/10/")result={data:data.lead};
      else if(path==="/api/assessments/30/")result={data:data.assessment};
      else if(path==="/api/quotes/40/")result={data:data.quote};
      else result={data:{id:99}};
    }
    const status=result.status||200;
    return {ok:status>=200&&status<300,status,json:async()=>structuredClone(result.data)};
  };
  w.eval(source);
  await waitFor(()=>w.document.querySelector(authenticated?"#main":"#login"));
  if(authenticated)await waitFor(()=>w.document.querySelector("#main")?.getAttribute("aria-busy")==="false");
  const select=selector=>w.document.querySelector(selector);
  const click=selector=>{const el=select(selector);assert.ok(el,selector);el.click();return el;};
  const fill=(selector,value)=>{const el=select(selector);assert.ok(el,selector);el.value=value;return el;};
  const submit=selector=>select(selector).dispatchEvent(new w.Event("submit",{bubbles:true,cancelable:true}));
  return {w,data,calls,select,click,fill,submit};
}

test("money strings retain precision and format without Number conversion",()=>{
  assert.equal(utils.money("9999999999999999.99","KES"),"KES 9,999,999,999,999,999.99");
});
test("measurement/user strings are escaped for text and attributes",()=>{
  assert.equal(utils.escapeHTML('<img src=x onerror="boom">'),"&lt;img src=x onerror=&quot;boom&quot;&gt;");
});
test("date inputs use explicit Nairobi offset regardless of browser locale",()=>{
  assert.equal(utils.nairobiInput("2027-01-02T07:30:00Z"),"2027-01-02T10:30");
  assert.equal(utils.fromNairobiInput("2027-01-02T10:30"),"2027-01-02T10:30:00+03:00");
  assert.throws(()=>utils.fromNairobiInput("bad"),/date and time/);
});
test("task origins navigate to their source workflows",()=>{
  assert.deepEqual(utils.routeForAction({id:1,origin_key:"quote:40:review"}),{type:"quote",id:40});
  assert.deepEqual(utils.routeForAction({id:2,consultation:20}),{type:"visit",id:20});
  assert.deepEqual(utils.routeForAction({id:3}),{type:"action",id:3});
});
test("manual lead stages never offer assessment, quoted or won shortcuts",()=>{
  assert.deepEqual(utils.leadTargets("QUALIFIED"),["DORMANT","LOST"]);
  assert.deepEqual(utils.leadTargets("WON"),[]);
});
test("anonymous sign-in sends CSRF and opens workspace",async t=>{
  const app=await harness(t,{authenticated:false});
  app.fill('[name="username"]',"owner");
  app.fill('[name="password"]',"local-test-password");
  app.submit("#login");
  await waitFor(()=>app.select("#main")?.textContent.includes("Good work"));
  const request=app.calls.find(c=>c.path==="/api/session/login/");
  assert.equal(request.options.headers["X-CSRFToken"],"csrf-local-test");
  assert.equal(request.payload.username,"owner");
  assert.equal(app.select("#login"),null);
});
test("workspace renders real queue counts and refresh control",async t=>{
  const data=baseData();
  data.actions=[{id:3,lead:10,title:"Call customer",customer_name:"Amina",assignee:1,due_at:null,version:1}];
  const app=await harness(t,{data});
  assert.ok(app.select('[data-action="refresh"]'));
  assert.match(app.select("#main").textContent,/Call customer/);
  app.click('[data-action="task"]');
  await waitFor(()=>app.select("#modal").open);
  app.fill('#modal [name="note"]',"Called and recorded request");
  app.submit("#editor");
  await waitFor(()=>app.calls.some(c=>c.path==="/api/actions/3/complete/"));
  const request=app.calls.find(c=>c.path==="/api/actions/3/complete/");
  assert.equal(request.payload.expected_version,1);
  assert.equal(request.options.headers["X-Organization-ID"],"1");
});
test("customer content is displayed as text, never executable markup",async t=>{
  const data=baseData();
  data.customers[0].name='<img src=x onerror="boom">';
  const app=await harness(t,{data,hash:"inquiries"});
  assert.match(app.select("#main").textContent,/<img src=x/);
  assert.equal(app.select("#main img"),null);
});
test("new inquiry submits selected company/customer with recorded brief",async t=>{
  const app=await harness(t,{hash:"inquiries"});
  app.click('[data-action="new-inquiry"]');
  app.fill('#modal [name="brief"]',"Refresh lounge flooring");
  app.submit("#editor");
  await waitFor(()=>app.calls.some(c=>c.path==="/api/leads/"&&c.options.method==="POST"));
  const request=app.calls.find(c=>c.path==="/api/leads/"&&c.options.method==="POST");
  assert.equal(request.payload.customer,5);
  assert.equal(request.payload.brief,"Refresh lounge flooring");
  assert.equal(request.options.headers["X-Organization-ID"],"1");
});
test("stale stage updates keep entered note and show a recoverable conflict",async t=>{
  const app=await harness(t,{hash:"inquiry/10/overview",handler:async call=>{
    if(call.path==="/api/leads/10/transition/")return {status:409,data:{detail:"Record changed"}};
  }});
  app.click('[data-action="lead-stage"]');
  await waitFor(()=>app.select("#modal").open);
  app.fill('#modal [name="note"]',"Called customer");
  app.submit("#editor");
  await waitFor(()=>!app.select("#form-error").hidden);
  assert.ok(app.select("#modal").open);
  assert.match(app.select("#form-error").textContent,/Refresh the record/);
  assert.equal(app.select('#modal [name="note"]').value,"Called customer");
});
test("assessment editor sends null unknown dimensions and string quantities",async t=>{
  const data=baseData();data.lead.assessments=[];data.lead.quotes=[];
  const app=await harness(t,{data,hash:"inquiry/10/visits"});
  app.click('[data-action="new-assessment"]');
  app.fill('#modal [name="scope"]',"Paint lounge");
  app.fill('#modal [name="measurement-label"]',"Room length");
  app.submit("#editor");
  await waitFor(()=>app.calls.some(c=>c.path==="/api/consultations/20/assessment/"));
  const request=app.calls.find(c=>c.path==="/api/consultations/20/assessment/");
  assert.equal(request.payload.measurements[0].value,null);
  assert.equal(request.payload.measurements[0].required,true);
});
test("quotation editor submits decimal strings, not client-computed totals",async t=>{
  const data=baseData();data.lead.quotes=[];
  const app=await harness(t,{data,hash:"inquiry/10/assessments"});
  app.click('[data-action="new-quote"]');
  await waitFor(()=>app.select(".quote-line"));
  app.fill('[name="line-description"]',"Paint");
  app.fill('[name="line-price"]',"1200.50");
  app.fill('[name="line-quantity"]',"2.125");
  app.submit("#editor");
  await waitFor(()=>app.calls.some(c=>c.path==="/api/assessments/30/quote/"));
  const request=app.calls.find(c=>c.path==="/api/assessments/30/quote/");
  assert.equal(request.payload.items[0].unit_price,"1200.50");
  assert.equal(request.payload.items[0].quantity,"2.125");
  assert.equal(request.payload.expected_assessment_version,2);
  assert.equal("total" in request.payload,false);
});
test("owner can open reviewed quotation and record internal approval",async t=>{
  const app=await harness(t,{hash:"inquiry/10/quotes"});
  app.click('[data-action="quote"]');
  await waitFor(()=>app.select("#approve-quote"));
  assert.ok(app.select("#submit-button").hidden);
  assert.match(app.select("#modal-body").textContent,/KES 2,000.00/);
  app.click("#approve-quote");
  assert.equal(app.select("#submit-button").hidden,false);
  app.fill('#modal [name="note"]',"Checked scope and prices");
  app.submit("#editor");
  await waitFor(()=>app.calls.some(c=>c.path==="/api/quotes/40/review/"));
  const request=app.calls.find(c=>c.path==="/api/quotes/40/review/");
  assert.equal(request.payload.command,"approve");
  assert.equal(request.payload.expected_version,2);
});
test("designer sees draft tools but no owner approval control",async t=>{
  const app=await harness(t,{data:baseData("DESIGNER"),hash:"inquiry/10/quotes"});
  app.click('[data-action="quote"]');
  await waitFor(()=>app.select("#quote-source"));
  assert.equal(app.select("#approve-quote"),null);
  assert.ok(app.select("#revise-quote"));
});
test("field staff navigation excludes private directories",async t=>{
  const app=await harness(t,{data:baseData("FIELD")});
  assert.equal(app.select('[data-nav="inquiries"]'),null);
  assert.equal(app.select('[data-nav="customers"]'),null);
  assert.equal(app.calls.some(c=>c.path==="/api/customers/"),false);
  assert.equal(app.calls.some(c=>c.path==="/api/staff/"),false);
});
test("switching company clears office records and sends new company header",async t=>{
  const app=await harness(t,{hash:"inquiries"});
  assert.match(app.select("#main").textContent,/Amina/);
  app.fill("#company","2").dispatchEvent(new app.w.Event("change",{bubbles:true}));
  await waitFor(()=>app.select("#main")?.textContent.includes("Good work"));
  assert.equal(app.select('[data-nav="customers"]'),null);
  assert.doesNotMatch(app.select("#main").textContent,/Amina/);
  assert.ok(app.calls.some(c=>c.path==="/api/today/"&&c.options.headers["X-Organization-ID"]==="2"));
});
test("failed data request renders an error instead of invented records",async t=>{
  const app=await harness(t,{handler:async call=>{
    if(call.path==="/api/customers/")return {status:503,data:{detail:"Database unavailable"}};
  }});
  assert.match(app.select("#main").textContent,/Database unavailable/);
  assert.ok(app.select('[data-action="refresh"]'));
});

test("quotation register filters pending reviews by status and customer",async t=>{
  const data=baseData();
  data.quotes=[data.quote,{...data.quote,id:41,status:"DRAFT",customer_name:"Brian"}];
  const app=await harness(t,{data,hash:"quotes"});
  assert.match(app.select("#quote-list").textContent,/Amina/);
  assert.match(app.select("#quote-list").textContent,/Brian/);
  app.fill("#quote-filter","READY_FOR_REVIEW").dispatchEvent(new app.w.Event("change",{bubbles:true}));
  assert.match(app.select("#quote-list").textContent,/Amina/);
  assert.doesNotMatch(app.select("#quote-list").textContent,/Brian/);
  app.fill("#quote-search","missing").dispatchEvent(new app.w.Event("input",{bubbles:true}));
  assert.match(app.select("#quote-list").textContent,/No matching quotations/);
});
test("only owners see team management navigation",async t=>{
  const app=await harness(t,{data:baseData("DESIGNER")});
  assert.equal(app.select('[data-nav="team"]'),null);
});
test("owner team form sends initial password only in the create request",async t=>{
  const app=await harness(t,{hash:"team"});
  app.click('[data-action="team-new"]');
  app.fill('#modal [name="name"]',"New designer");
  app.fill('#modal [name="username"]',"new-designer");
  app.fill('#modal [name="password"]',"Initial-Passphrase!2026");
  app.submit("#editor");
  await waitFor(()=>app.calls.some(c=>c.path==="/api/team/"&&c.options.method==="POST"));
  const call=app.calls.find(c=>c.path==="/api/team/"&&c.options.method==="POST");
  assert.equal(call.payload.role,"DESIGNER");
  assert.equal(call.options.headers["X-Organization-ID"],"1");
});
test("quote print link carries company context and isolates the new tab",async t=>{
  const app=await harness(t,{hash:"inquiry/10/quotes"});
  app.click('[data-action="quote"]');
  await waitFor(()=>app.select(".print-link"));
  assert.equal(app.select(".print-link").getAttribute("href"),"/quotes/40/print/?organization=1");
  assert.equal(app.select(".print-link").getAttribute("rel"),"noopener");
});
test("password confirmation mismatch is caught before sending credentials",async t=>{
  const app=await harness(t);
  app.click('[data-action="password"]');
  app.fill('#modal [name="current_password"]',"Original-Passphrase!2026");
  app.fill('#modal [name="new_password"]',"New-Passphrase!2026");
  app.fill('#modal [name="confirm_password"]',"Different-Passphrase!2026");
  app.submit("#editor");
  await waitFor(()=>!app.select("#form-error").hidden);
  assert.match(app.select("#form-error").textContent,/do not match/);
  assert.equal(app.calls.some(c=>c.path==="/api/session/password/"),false);
});
