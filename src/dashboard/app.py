"""Real HBase-backed, retrospective one-hour demand dashboard."""
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

load_dotenv(ROOT/'.env', override=False)
from src.dashboard import service as api

st.set_page_config(page_title='NYC Taxi Demand', page_icon='🚕', layout='wide')
st.html('''<style>
[data-testid="stMainBlockContainer"]{max-width:1440px;padding-top:5rem;padding-bottom:3rem}
[data-testid="stMetric"]{background:rgba(128,128,128,.06);border:1px solid rgba(128,128,128,.25);border-radius:18px;padding:18px;min-height:130px}
[data-testid="stMetricValue"]{font-variant-numeric:tabular-nums}
[data-testid="stMetricLabel"]{opacity:.85}
h1{letter-spacing:-.04em}h2,h3{letter-spacing:-.025em}
button:focus-visible,a:focus-visible{outline:2px solid currentColor!important;outline-offset:3px}
@media(max-width:700px){[data-testid="stMainBlockContainer"]{padding:4.8rem 1rem 2rem} [data-testid="stMetric"]{min-height:100px;padding:14px}}
</style>''')


@st.cache_data(ttl=60, show_spinner=False)
def health():
    return api.status()


@st.cache_data(ttl=300, show_spinner=False)
def cached(kind, *args):
    return getattr(api,kind)(*args)


@st.cache_data(show_spinner=False)
def lookup():
    return api.zones()


def checked(operation):
    try:
        return operation()
    except Exception as error:
        st.error('Không đọc được dữ liệu đầy đủ. Màn hình không tự thay dữ liệu thiếu bằng 0.')
        st.caption('Bật Docker Desktop/HBase và chạy bước Load theo hướng dẫn giai đoạn 5. Sau đó bấm Kiểm tra lại kết nối.')
        with st.expander('Chi tiết để kiểm tra'):
            st.code(f'{type(error).__name__}: {error}', language=None)
        st.stop()


def fmt(value, decimals=0):
    if value is None or pd.isna(value):
        return 'Chưa có'
    return f'{value:,.{decimals}f}'.replace(',','_').replace('.',',').replace('_','.')


def chart(fig, key):
    # Native frontend theming updates charts immediately without a Python rerun.
    fig.update_layout(template='streamlit', paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)', font=dict(family='Segoe UI, Arial',size=13),
        margin=dict(l=16,r=16,t=20,b=25), legend=dict(orientation='h',y=1.14),
        hovermode='x unified', height=370, yaxis=dict(rangemode='tozero'))
    st.plotly_chart(fig, width='stretch', key=key,
        config={'displaylogo':False,'scrollZoom':False,'toImageButtonOptions':{'format':'png'}})


def zone_picker(key, comparison=False):
    items=lookup().set_index('LocationID')
    options=[int(z) for z in items.index]
    if comparison:options=[None]+options
    return st.selectbox('Vùng so sánh' if comparison else 'Khu vực',options,
        index=0 if comparison else options.index(161), key=key,
        format_func=lambda z:'Không so sánh' if z is None else f'{z:03d} · {items.loc[z,"Zone"]} · {items.loc[z,"Borough"]}')


def date_range(key):
    chosen=st.date_input('Khoảng ngày · tối đa 31 ngày',value=(date(2025,1,1),date(2025,1,7)),
        min_value=api.START,max_value=api.END,key=key,format='DD/MM/YYYY')
    if len(chosen)!=2:
        st.info('Chọn đủ ngày bắt đầu và kết thúc.');st.stop()
    try:api.check_range(*chosen)
    except ValueError as e:st.warning(str(e));st.stop()
    return chosen


def add_names(frame):
    return frame.merge(lookup()[['LocationID','Zone','Borough']],left_on='zone',right_on='LocationID',how='left',validate='many_to_one')


def export(frame,filename,key):
    st.download_button('Tải bảng CSV',frame.to_csv(index=False).encode('utf-8-sig'),
        filename,'text/csv',key=key)


def overview():
    st.title('Hiểu nhu cầu. Theo dõi lượt đón.')
    st.write('Nhìn vào thời gian và khu vực có nhiều lượt đón taxi ghi nhận.')
    start,end=date_range('overview_dates')
    with st.spinner('Đang đọc tổng hợp từ HBase…'):
        frame=checked(lambda:cached('daily',start,end))
    st.caption(f'{start:%d/%m/%Y}–{end:%d/%m/%Y} · 263 vùng · Giờ địa phương New York')
    if frame['missing'].sum():st.warning('Có giờ thiếu nguồn. Tổng bên dưới chỉ gồm lượt đón đã ghi nhận.')
    top=add_names(frame.groupby('zone',as_index=False).agg(recorded=('recorded',lambda s:s.sum(min_count=1)))).sort_values('recorded',ascending=False)
    total=frame.recorded.sum(min_count=1)
    a,b,c=st.columns(3)
    a.metric('Lượt đón ghi nhận',fmt(total))
    b.metric('Trung bình mỗi ngày',fmt(total/((end-start).days+1)))
    c.metric('Vùng nhiều lượt đón nhất',f'{int(top.iloc[0].zone):03d}',help=top.iloc[0].Zone)
    left,right=st.columns([1.7,1],gap='large')
    with left:
        st.subheader('Xu hướng theo ngày')
        daily=frame.groupby('period',as_index=False).agg(recorded=('recorded',lambda s:s.sum(min_count=1)))
        daily['Ngày']=pd.to_datetime(daily.period,format='%Y%m%d')
        chart(px.line(daily,x='Ngày',y='recorded',markers=True,labels={'recorded':'Lượt đón/ngày'}),'overview_trend')
    with right:
        st.subheader('10 vùng có nhiều lượt đón')
        chart(px.bar(top.head(10).sort_values('recorded'),x='recorded',y='Zone',orientation='h',
            labels={'recorded':'Lượt đón','Zone':'Vùng'}),'overview_top')
    st.subheader('Toàn bộ 36 tháng')
    monthly=checked(lambda:cached('monthly')).groupby('period',as_index=False).agg(recorded=('recorded','sum'))
    monthly['Tháng']=pd.to_datetime(monthly.period,format='%Y%m')
    chart(px.line(monthly,x='Tháng',y='recorded',markers=True,labels={'recorded':'Lượt đón/tháng'}),'overview_monthly')
    export(add_names(frame),'nhu_cau_theo_ngay.csv','overview_csv')


def map_page():
    st.title('Nhu cầu trên bản đồ')
    st.write('Màu sắc thể hiện số lượt đón ghi nhận trong một giờ tại các vùng taxi.')
    a,b=st.columns(2)
    with a:day=st.date_input('Ngày',date(2025,1,7),min_value=api.START,max_value=api.END,key='map_day',format='DD/MM/YYYY')
    with b:hour=st.select_slider('Giờ đón · New York',options=list(range(24)),value=12,format_func=lambda h:f'{h:02d}:00',key='map_hour')
    with st.spinner('Đang đọc 263 vùng…'):frame=checked(lambda:add_names(cached('snapshot',day,hour)))
    path=ROOT/'data/reference/taxi_zones.geojson'
    if not path.exists():st.error('Chưa có ranh giới vùng chính thức. Chạy bước Geometry.');st.stop()
    geometry=json.loads(path.read_text(encoding='utf-8'))
    if frame.dst.any():st.warning('Ngày đổi giờ DST: giữ số đếm để mô tả; không dùng làm nhãn đánh giá model.')
    fig=go.Figure(go.Choropleth(geojson=geometry,featureidkey='properties.zone',
        locations=frame.zone,z=frame.recorded,customdata=frame[['Zone','Borough']].to_numpy(),
        colorscale=[[0,'#EDF3EA'],[0.25,'#A4C695'],[0.65,'#609944'],[1,'#347A25']],
        marker_line_color='#8B99AC',marker_line_width=0.5,colorbar=dict(title='Lượt/giờ',thickness=12,len=0.75),
        hovertemplate='Vùng %{location} · %{customdata[0]}<br>%{customdata[1]}<br>%{z} lượt đón<extra></extra>'))
    fig.update_layout(template='streamlit',geo=dict(visible=False,fitbounds='locations',projection_type='mercator',bgcolor='rgba(0,0,0,0)'),
        height=500,margin=dict(l=0,r=0,t=0,b=0),
        paper_bgcolor='rgba(0,0,0,0)',font=dict(size=13))
    st.plotly_chart(fig,width='stretch',key='zone_map',config={'displaylogo':False,'scrollZoom':False})
    st.caption(f'{day:%d/%m/%Y} · {hour:02d}:00–{hour+1:02d}:00 · Ranh giới chính thức NYC TLC · Có vùng Newark Airport ngoài NYC')
    st.dataframe(frame[['zone','Zone','Borough','recorded','dst','missing']].sort_values('recorded',ascending=False),
        hide_index=True,width='stretch',column_config={'zone':'Mã vùng','Zone':'Tên vùng','Borough':'Khu vực','recorded':'Lượt đón','dst':'Ngày DST','missing':'Thiếu nguồn'})


def analysis():
    st.title('Phân tích từng khu vực')
    a,b=st.columns(2)
    with a:zone=zone_picker('analysis_zone')
    with b:other=zone_picker('analysis_other',True)
    start,end=date_range('analysis_dates')
    with st.spinner('Đang đọc lịch sử theo giờ…'):frame=checked(lambda:cached('history',zone,start,end))
    all_frames=[frame.assign(Vùng=f'{zone:03d}')]
    if other is not None and other!=zone:
        all_frames.append(checked(lambda:cached('history',other,start,end)).assign(Vùng=f'{other:03d}'))
    plot=pd.concat(all_frames,ignore_index=True)
    a,b,c=st.columns(3)
    a.metric('Lượt đón của vùng',fmt(frame.recorded.sum(min_count=1)))
    b.metric('Giờ thiếu nguồn',fmt(frame.missing.sum()))
    c.metric('Giờ thuộc ngày DST',fmt(frame.dst.sum()))
    chart(px.line(plot,x='hour',y='recorded',color='Vùng',labels={'hour':'Giờ địa phương New York','recorded':'Lượt đón/giờ'}),'analysis_history')
    frame['weekday']=frame.hour.dt.weekday;frame['clock']=frame.hour.dt.hour
    heat=frame.pivot_table(index='weekday',columns='clock',values='recorded',aggfunc='mean').reindex(index=range(7),columns=range(24))
    st.subheader('Nhịp nhu cầu theo thứ và giờ')
    st.caption('Trung bình lượt đón/giờ trong khoảng chọn. Ô không có quan sát để trống; không điền 0.')
    fig=go.Figure(go.Heatmap(z=heat.to_numpy(),x=list(range(24)),y=['Thứ 2','Thứ 3','Thứ 4','Thứ 5','Thứ 6','Thứ 7','Chủ nhật'],
        colorscale='Viridis',colorbar=dict(title='Lượt/giờ'),hoverongaps=False,
        hovertemplate='%{y} · %{x}:00<br>%{z:.2f} lượt/giờ<extra></extra>'))
    fig.update_layout(xaxis_title='Giờ địa phương New York',yaxis_title='Thứ trong tuần')
    chart(fig,'analysis_heatmap')
    export(frame,'lich_su_vung_theo_gio.csv','analysis_csv')


def metric_cards(values):
    a,b,c=st.columns(3)
    a.metric('MAE · lượt/giờ/vùng',fmt(values['mae'],2))
    b.metric('RMSE · lượt/giờ/vùng',fmt(values['rmse'],2))
    c.metric('WAPE',fmt(values['wape']*100,2)+'%' if values['wape'] is not None else 'Không xác định')


def forecast():
    st.title('Dự báo và kiểm chứng')
    st.info('Phát lại lịch sử năm 2025 · Dự báo một giờ · Chỉ dùng các giờ trước giờ đích. Số thực tế được mở riêng để đối chiếu.')
    a,b,c=st.columns([2,1,1])
    with a:zone=zone_picker('forecast_zone')
    with b:day=st.date_input('Ngày đích',date(2025,1,7),min_value=date(2025,1,1),max_value=api.END,key='forecast_day',format='DD/MM/YYYY')
    with c:clock=st.selectbox('Giờ đích',range(24),index=12,format_func=lambda h:f'{h:02d}:00',key='forecast_hour')
    target=datetime.combine(day,datetime.min.time()).replace(hour=clock)
    with st.spinner('Đang đọc dự báo đã lưu và lịch sử…'):
        frame=checked(lambda:cached('joined',zone,day,day))
        previous=checked(lambda:cached('history',zone,max(api.START,day-timedelta(days=1)),day))
    selected=frame.loc[frame.hour==target].iloc[0]
    predict_tab,score_tab,ledger_tab=st.tabs(['Dự báo một giờ','Đánh giá sai số','Sổ dự báo'])
    with predict_tab:
        st.caption(f'Vùng {zone:03d} · Giờ đích {target:%d/%m/%Y %H:%M}–{(target+timedelta(hours=1)):%H:%M} · America/New_York')
        st.write('Lịch sử đầu vào kết thúc trước giờ đích. “Giờ gốc” trong bảng là giờ quan sát cuối đã hoàn tất.')
        if pd.isna(selected.prediction):
            st.warning('Giờ này không có dự báo được nghiệm thu: ngày DST hoặc nhãn nguồn không hợp lệ. Không tự sinh kết quả giả.')
            st.metric('Lượt đón ghi nhận để mô tả',fmt(selected.recorded))
        else:
            a,b=st.columns(2)
            a.metric('Lượt đón dự kiến',fmt(selected.prediction,2))
            b.metric('Baseline · cùng giờ tuần trước hoặc dự phòng',fmt(selected.baseline,2))
            st.write('Phương án sử dụng: **'+api.METHODS.get(selected.method,selected.method)+'**')
            if selected.method!='random_forest':st.warning('Thiếu đặc trưng quá khứ hợp lệ; đã dùng dự phòng được duyệt.')
            if st.checkbox('Mở số thực tế để kiểm chứng',key='reveal_actual'):
                a,b=st.columns(2)
                a.metric('Thực tế · lượt đón',fmt(selected.actual))
                b.metric('Sai số tuyệt đối · lượt',fmt(abs(selected.prediction-selected.actual),2))
                st.caption('Một điểm chưa đủ kết luận chất lượng model. Xem đánh giá trên nhiều giờ ở tab kế bên.')
        history=previous.loc[previous.hour<target].tail(24)
        st.subheader('24 giờ lịch sử trước mốc dự báo')
        chart(px.line(history,x='hour',y='recorded',markers=True,labels={'hour':'Giờ địa phương New York','recorded':'Lượt đón/giờ'}),'forecast_context')
        st.caption('Dự báo tính sẵn từ model giai đoạn 4 và đọc từ HBase, không huấn luyện lại khi chọn giờ. Hệ thống chưa có nguồn cập nhật trực tiếp.')
    with score_tab:
        st.subheader('Đánh giá vùng và ngày đang chọn')
        valid=api.evaluated(frame)
        if valid.empty:st.info('Không có nhãn hợp lệ để tính sai số trong ngày này.')
        else:
            metric_cards(api.metrics(valid))
            st.caption(f'{len(valid)} giờ hợp lệ · Vùng {zone:03d} · {day:%d/%m/%Y} · Không gồm ngày DST/nhãn thiếu')
            plot=valid.melt(id_vars=['hour'],value_vars=['actual','prediction','baseline'],var_name='Chuỗi',value_name='Lượt đón/giờ')
            plot['Chuỗi']=plot['Chuỗi'].map({'actual':'Thực tế','prediction':'RF + dự phòng','baseline':'Baseline'})
            chart(px.line(plot,x='hour',y='Lượt đón/giờ',color='Chuỗi',markers=True,labels={'hour':'Giờ địa phương New York'}),'forecast_compare')
            comparison=pd.DataFrame([{'Phương án':label,**api.metrics(valid,col)} for col,label in [('prediction','RF + dự phòng'),('baseline','Baseline')]])
            comparison['wape']=comparison.wape*100
            st.dataframe(comparison.rename(columns={'n':'Số giờ','mae':'MAE','rmse':'RMSE','wape':'WAPE (%)'}),hide_index=True,width='stretch')
        st.subheader('Kết quả toàn tập test 2025')
        final=json.loads((ROOT/'artifacts/metrics/stage4_final.json').read_text())
        metric_cards(final['system'])
        st.caption(f'{fmt(final["system"]["n"])} nhãn vùng–giờ · Model cố định, gồm cơ chế dự phòng. Đây không phải độ đo của bộ lọc phía trên.')
        st.write('MAE giảm **27,61%** so với baseline. WAPE là sai số tương đối tổng hợp, không phải accuracy. MAE trung bình không bảo đảm mỗi điểm sai dưới 4 lượt.')
        bymonth=pd.DataFrame(final['by_month'])
        chart(px.bar(bymonth,x='month',y='mae',labels={'month':'Tháng năm 2025','mae':'MAE · lượt/giờ/vùng'}),'forecast_month_error')
    with ledger_tab:
        st.caption('Các dự báo và nhãn của ngày đang chọn. Ô trống nghĩa là chưa có/không dùng để đánh giá; không phải 0.')
        ledger=frame[['hour','origin_hour','prediction','baseline','actual','method','model_version','eligible','dst','missing']].copy()
        ledger['method']=ledger.method.map(api.METHODS)
        st.dataframe(ledger,hide_index=True,width='stretch',column_config={'hour':'Giờ đích','origin_hour':'Giờ quan sát cuối','prediction':'Dự báo','baseline':'Baseline','actual':'Thực tế hợp lệ','method':'Phương án','model_version':'Phiên bản','eligible':'Đánh giá được','dst':'Ngày DST','missing':'Thiếu nguồn'})
        export(ledger,'doi_chieu_du_bao.csv','forecast_csv')


def information():
    st.title('Dữ liệu và mô hình')
    st.write('Phạm vi thực nghiệm: phân tích và dự báo số lượt đón Yellow Taxi ghi nhận tại New York. Không đo khách chưa được phục vụ hoặc nhu cầu của toàn bộ giao thông công cộng.')
    a,b,c=st.columns(3)
    a.metric('Dữ liệu nguồn', '36 tháng')
    b.metric('Vùng dự báo','263')
    c.metric('Khoảng dự báo','1 giờ')
    st.subheader('Nguồn và cách xử lý')
    st.markdown('Nguồn: [NYC TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page). **01/2023–12/2025**: 128.202.548 dòng nguồn; giữ 126.994.028 chuyến. Spark tạo số đếm theo vùng–giờ; HBase lưu lịch sử, dự báo và tổng hợp phục vụ giao diện.')
    st.write('Giữ bản raw và các nhóm cách ly. Không biến giá trị thiếu thành 0. Hai ngày đổi giờ mỗi năm giữ số đếm cho phân tích nhưng che nhãn huấn luyện/đánh giá do timestamp không có UTC offset.')
    st.subheader('Huấn luyện và kiểm thử')
    st.write('So sánh lịch sử 2024 và 2023–2024 qua validation tháng 10–12/2024. Khóa Random Forest 20 cây, độ sâu 12; huấn luyện cuối bằng 2023–2024 rồi kiểm thử 2025. Không học từ nhãn tương lai khi tạo dự báo.')
    st.write('Đầu vào: số lượt đón trễ 1, 2, 24, 168 giờ; trung bình 24/168 giờ; giờ, thứ và mã vùng. Thiếu đầu vào: dùng cùng giờ tuần trước, rồi trung bình vùng từ train, cuối cùng trung bình toàn train nếu cần.')
    st.subheader('Cách đọc độ đo')
    st.markdown('- **MAE:** sai số tuyệt đối trung bình, đơn vị lượt/giờ/vùng.\n- **RMSE:** nhạy hơn với những sai số lớn, cùng đơn vị MAE.\n- **WAPE:** tổng sai số tuyệt đối chia tổng lượt đón thực tế; không xác định khi tổng thực tế bằng 0.\n- **Baseline:** mốc so sánh đơn giản để biết model có cải thiện không.')
    st.subheader('Giới hạn và phiên bản')
    st.write('Demo phát lại lịch sử, không phải hệ thống thời gian thực. Dự báo một giờ không tương đương dự báo cả năm. Dữ liệu TLC có độ trễ công bố; timestamp và chất lượng nguồn có giới hạn. Không hiển thị khoảng tin cậy khi chưa xây dựng và kiểm chứng phương pháp tương ứng.')
    prep=ROOT/'artifacts/metrics/stage5_prepared.json'
    if prep.exists():
        info=json.loads(prep.read_text())
        st.caption(f'Model: stage4_final · Dataset: hourly_grid_v1 · Dashboard: dashboard_v1 · Snapshot phục vụ tạo lúc {info["built_at_utc"]} (UTC)')
    with st.expander('Hướng dẫn thao tác'):
        st.write('Tổng quan: lọc tối đa 31 ngày và xem xu hướng cả 36 tháng. Bản đồ: chọn ngày/giờ. Phân tích vùng: chọn vùng và khoảng ngày. Dự báo: chọn một giờ năm 2025, mở số thực tế, xem sai số và tải CSV. Biểu đồ hỗ trợ zoom và tải ảnh từ thanh công cụ.')


st.caption('NYC TAXI DEMAND  /  PHÂN TÍCH & DỰ BÁO')
st.caption('Dữ liệu lịch sử 2023–2025 · Giờ địa phương New York · Dự báo được kiểm chứng trên 2025')
with st.sidebar:
    st.markdown('### 🚕 NYC Taxi Demand')
    st.caption('Spark · HBase · Random Forest')
    if st.button('Kiểm tra lại kết nối',width='stretch'):
        health.clear();cached.clear();st.rerun()
    checked(health)
    st.success('HBase đã kết nối')
    st.caption('Sáng / tối: mở **⋮ → Light / Dark** ở góc trên bên phải.')
    with st.container(border=True):
        st.markdown('**Phạm vi dữ liệu**')
        st.write('2023–2025 · 36 tháng · 263 vùng')
        st.caption('126.994.028 chuyến sau làm sạch')
    with st.container(border=True):
        st.markdown('**Kiểm chứng năm 2025**')
        st.write('MAE **3,85** · WAPE **18,46%**')
        st.caption('2.291.256 nhãn vùng–giờ · RF + dự phòng')
        st.caption('MAE: lượt/giờ/vùng · WAPE: sai số')
    with st.expander('Cách dùng nhanh'):
        st.write('**1.** Tổng quan hoặc Bản đồ: xem lượt đón theo thời gian và khu vực.')
        st.write('**2.** Dự báo & kiểm chứng: chọn giờ năm 2025, mở số thực tế rồi xem sai số.')
        st.caption('Giờ địa phương: America/New_York. Ngày DST giữ số đếm nhưng không dùng làm nhãn đánh giá.')
    st.caption('Phát lại lịch sử · Dự báo một giờ\n\nDữ liệu chưa cập nhật trực tiếp.')
pages=[st.Page(overview,title='Tổng quan',url_path='tong-quan',default=True),
       st.Page(map_page,title='Bản đồ',url_path='ban-do'),
       st.Page(analysis,title='Phân tích vùng',url_path='phan-tich'),
       st.Page(forecast,title='Dự báo & kiểm chứng',url_path='du-bao'),
       st.Page(information,title='Dữ liệu & mô hình',url_path='thong-tin')]
checked(lambda:st.navigation(pages,position='top').run())
