import streamlit as st
import pandas as pd
from docx import Document
from io import BytesIO
import asyncio
from claude_agent_sdk import tool, create_sdk_mcp_server, ClaudeAgentOptions, query, ResultMessage
import re

SETTINGS = {
    "app_title": "Verified Contract Assistant",
    "item name":"contract",
    "id_column":"Contract_ID",
    "name_column":"Client",
    "start_column":"Start_Date",
    "end_column":"End_Date",
    "value_column":"Value_GBP",
    "notice_column":"Notice_Days",
    "currency":"$",
    "alert_days":60,
}

st.set_page_config(page_title=SETTINGS["app_title"],layout="wide")
st.title(SETTINGS["app_title"])

file = st.file_uploader(f"Upload your {SETTINGS["item name"]} register",type=["csv"])
if file is None:
    st.write("Please upload your file")
    st.stop()
else:
    df=pd.read_csv(file)
    st.dataframe(df)

start = pd.to_datetime(df[SETTINGS["start_column"]],format="%Y-%m-%d",errors="coerce")
end = pd.to_datetime(df[SETTINGS["end_column"]],format="%Y-%m-%d",errors="coerce")

st.header("Data Quality Check")

missing =df[df.isnull().any(axis=1)]
duplicates=df[df.duplicated(subset=[SETTINGS["id_column"]])]
bad_dates=df[start.isnull()|end.isnull()]
negative=df[df[SETTINGS["value_column"]]<0]
end_before_start=df[end < start]

st.write("Missing fields:",len(missing))
st.dataframe(missing)

st.write("Duplicates:",len(duplicates))
st.dataframe(duplicates)

st.write("Invalid Dates:",len(bad_dates))
st.dataframe(bad_dates)

st.write("Negative Values:",len(negative))
st.dataframe(negative)

st.write("End date before start date:",len(end_before_start))
st.dataframe(end_before_start)

bad_rows = set(missing.index)|set(duplicates.index)|set(bad_dates.index)|set(negative.index)|set(end_before_start.index)
clean = df.drop(index=list(bad_rows))

with st.expander("Show the clean data (rows used)"):
    st.dataframe(clean)

st.header("Renewal Deadline Alerts")
today=pd.Timestamp(st.date_input("Check Deadlines as of"))
clean=clean.copy()

end_date = pd.to_datetime(clean[SETTINGS["end_column"]])
Notice_Days = pd.to_timedelta(clean[SETTINGS["notice_column"]], unit="D")
clean["Notice_Date"]=end_date-Notice_Days

clean["Days_left"]=(clean["Notice_Date"]-today).dt.days
due_soon=clean[(clean["Days_left"]>=0)&(clean["Days_left"]<=SETTINGS["alert_days"])]

due_soon=due_soon.sort_values("Days_left")

st.write(f"Notice deadlines in the next {SETTINGS['alert_days']} days:",len(due_soon))
st.dataframe(due_soon)

st.header("Renewal Reminder Letter")
contract_list=due_soon[SETTINGS["id_column"]]
choose_id=st.selectbox("Choose a contract",contract_list)
row=due_soon[due_soon[SETTINGS["id_column"]]==choose_id].iloc[0]

client=row[SETTINGS["name_column"]]
end_date=pd.to_datetime(row[SETTINGS["end_column"]]).strftime("%d %B %Y")
notice_date=row["Notice_Date"].strftime("%d %B %Y")
today_text=today.strftime("%d %B %Y")
letter=Document("renewal_letter_template.docx")

for paragraph in letter.paragraphs:
    text=paragraph.text
    text=text.replace("{today}",today_text)
    text=text.replace("{client}",client)
    text=text.replace("{contract_id}",choose_id)
    text=text.replace("{end_date}",end_date)
    text=text.replace("{notice_date}",notice_date)
    paragraph.text=text

buffer=BytesIO()
letter.save(buffer)
st.download_button("Download Letter",buffer.getvalue(),file_name="Renewal Reminder "+choose_id+".docx")

st.header("Ask the Contract Assistant")

@tool ("find_contract", "Find one contract using  its ID, like C-103", {"contract_id":str})
async def find_contract(args):
    match=clean[clean[SETTINGS["id_column"]]==args["contract_id"]]
    text=match.to_string(index=False)
    return {"content":[{"type":"text","text":text}]}

@tool ("contracts_due_soon","List contracts with a notice deadline in the next 60 days",{})
async def contracts_due_soon(args):
    text=due_soon.to_string(index=False)
    return{"content":[{"type":"text","text":text}]}

@tool ("contracts_for_client","List all contracts for one client name",{"client":str})
async def contracts_for_client(args):
    match=clean[clean[SETTINGS["name_column"]].str.contains(args["client"],case=False)]
    text=match.to_string(index=False)
    return{"content":[{"type":"text","text":text}]}

toolbox=create_sdk_mcp_server(name="contracts",tools=[find_contract,contracts_due_soon,contracts_for_client])

rules = "Answer questions about the contract register. Always use the tools. Never guess. Write dates as YYYY-MM-DD. Write amounts like £45,000."
toolnames=["mcp__contracts__find_contract","mcp__contracts__contracts_due_soon","mcp__contracts__contracts_for_client"]
options=ClaudeAgentOptions(
    model="claude-haiku-5-5",
    system_prompt=rules,
    mcp_servers={"contracts":toolbox},
    allowed_tools=toolnames,
    tools=[],
    setting_sources=[],
    
)

async def ask_claude(questions):
    async for message in query(prompt=questions,options=options):
        if isinstance(message,ResultMessage):
            return message.result

questions=st.text_input("Ask a question about the contracts")
if st.button("Ask"):
    answer=asyncio.run(ask_claude(questions))
    st.write(answer)
    st.subheader("Validation")

    register = clean.to_string()+today.strftime("%Y-%m-%d")

    for date in re.findall(r"\d{4}-\d{2}-\d{2}",answer):
        if date in register:
            st.write("✅",date)
        else:
            st.write("⚠️",date,"Not in register")

    for amount in re.findall(r"£[\d,]+",answer):
        if amount.replace("£","").replace(",","")in register:
            st.write("✅",amount)
        else:
            st.write("⚠️",amount,"Not in register")

    for name in clean[SETTINGS["name_column"]]:
        if name in answer:
            st.write("✅", name)