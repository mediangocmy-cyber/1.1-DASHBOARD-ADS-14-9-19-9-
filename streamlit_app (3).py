import io, re
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

st.set_page_config(page_title='Ngọc Mỹ | TikTok Ads',page_icon='📊',layout='wide')
st.markdown('''<style>.block-container{padding-top:1.5rem;max-width:1500px}div[data-testid="stMetric"]{background:#f5f7fb;border:1px solid #e6eaf0;padding:14px;border-radius:14px}h1,h2,h3{letter-spacing:-.025em} .stAlert{border-radius:12px}</style>''',unsafe_allow_html=True)

def read_xlsx(file):
    return pd.read_excel(file,dtype={'ID chiến dịch':str,'ID sản phẩm':str,'ID bài đăng':str})

def read_orders(file):
    b=file.getvalue()
    for enc in ('utf-8-sig','utf-16','cp1258'):
        try:return pd.read_csv(io.BytesIO(b),encoding=enc,dtype=str,sep=None,engine='python')
        except (UnicodeError,ValueError):pass
    raise ValueError('Không đọc được file CSV')

def num(s):
    return pd.to_numeric(s.astype(str).str.replace(',','',regex=False).str.replace('₫','',regex=False).str.strip().replace({'-':None,'':None,'nan':None}),errors='coerce').fillna(0)

def clean_id(s):return s.astype(str).str.replace(r'\D','',regex=True)
def vnd(v):return f'{v:,.0f}đ'.replace(',','.')
def ratio(n,d):return n/d if d>0 else np.nan
def show_roas(v):return f'{v:.2f}' if pd.notna(v) else '—'

def find_col(df,options):
    for c in options:
        if c in df.columns:return c
    return None

st.title('📊 TikTok Shop | Hiệu quả Ads & đối soát đơn hủy')
st.caption('GMV Max • ROAS = Doanh thu / Chi phí Ads • Không cộng doanh thu từ nhiều cấp báo cáo')
with st.sidebar:
    st.header('1. Tải dữ liệu')
    overview_file=st.file_uploader('Campaign overview (.xlsx)',type=['xlsx'],key='overview')
    campaign_file=st.file_uploader('Product campaign (.xlsx)',type=['xlsx'],key='campaign')
    product_file=st.file_uploader('Product data (.xlsx)',type=['xlsx'],key='product')
    creative_file=st.file_uploader('Creative data (.xlsx)',type=['xlsx'],key='creative')
    order_file=st.file_uploader('Tất cả đơn hàng (.csv)',type=['csv'],key='orders')
    st.divider()
    st.header('2. Thiết lập')
    include_pending=st.toggle('Tính đơn chưa hủy nhưng chưa giao',value=True,help='Nếu tắt, chỉ tính đơn đã giao. Cả hai cách đều không phải doanh thu Ads được TikTok xác nhận.')
    st.caption('Tải từng tệp độc lập. Dashboard sẽ hiển thị những phần đủ dữ liệu.')

frames={}
for key,file,reader in [('overview',overview_file,read_xlsx),('campaign',campaign_file,read_xlsx),('product',product_file,read_xlsx),('creative',creative_file,read_xlsx),('orders',order_file,read_orders)]:
    if file is not None:
        try:frames[key]=reader(file)
        except Exception as e:st.error(f'Lỗi đọc {key}: {e}')
if not frames:
    st.info('Hãy tải các tệp xuất từ TikTok Ads và tệp đơn hàng ở thanh bên trái. Có thể tải 1–5 tệp, nhưng cần Campaign overview + CSV đơn hàng để tính ROAS điều chỉnh tham khảo.')
    st.stop()

ov=frames.get('overview');camp=frames.get('campaign');prod=frames.get('product');creative=frames.get('creative');orders=frames.get('orders')
if ov is not None:
    ov=ov.copy();ov['Chi phí']=num(ov['Chi phí']);ov['Doanh thu gộp (Cửa hàng hiện tại)']=num(ov['Doanh thu gộp (Cửa hàng hiện tại)']);ov['Theo ngày']=pd.to_datetime(ov['Theo ngày'],errors='coerce');ov=ov[ov['Theo ngày'].notna()]
if camp is not None:
    camp=camp.copy();camp['Chi phí']=num(camp['Chi phí']);camp['Doanh thu gộp']=num(camp['Doanh thu gộp']);camp['Số lượng đơn hàng SKU']=num(camp['Số lượng đơn hàng SKU']);camp['ID chiến dịch']=clean_id(camp['ID chiến dịch']);camp['ROAS tính lại']=camp.apply(lambda r:ratio(r['Doanh thu gộp'],r['Chi phí']),axis=1)
if prod is not None:
    prod=prod.copy();prod['Chi phí']=num(prod['Chi phí']);prod['Doanh thu gộp']=num(prod['Doanh thu gộp']);prod['Số lượng đơn hàng SKU']=num(prod['Số lượng đơn hàng SKU']);prod['ID sản phẩm']=clean_id(prod['ID sản phẩm']);prod['ID chiến dịch']=clean_id(prod['ID chiến dịch']);prod['ROAS tính lại']=prod.apply(lambda r:ratio(r['Doanh thu gộp'],r['Chi phí']),axis=1)
if creative is not None:
    creative=creative.copy()
    for c in ['Chi phí','Doanh thu gộp','Số lượng đơn hàng SKU','Số lượt hiển thị quảng cáo sản phẩm','Số lượt nhấp vào quảng cáo sản phẩm']:
        if c in creative:creative[c]=num(creative[c])
if orders is not None:
    orders=orders.copy()
    needed=['Order ID','Order Status','SKU ID','Order Amount','Product Name']
    missing=[c for c in needed if c not in orders]
    if missing:
        st.error('CSV thiếu cột: '+', '.join(missing));orders=None
    else:
        orders['Order ID']=clean_id(orders['Order ID']);orders['SKU ID']=clean_id(orders['SKU ID'])
        orders['Order Amount']=num(orders['Order Amount']);orders['Quantity']=num(orders['Quantity']) if 'Quantity' in orders else 1
        orders['Đã hủy']=orders['Order Status'].astype(str).str.contains('hủy|cancel',case=False,regex=True,na=False)
        orders['Đã giao']=orders['Order Status'].astype(str).str.contains('đã giao|delivered|completed|hoàn thành',case=False,regex=True,na=False)
        orders['Hợp lệ theo lựa chọn']=(~orders['Đã hủy']) & (True if include_pending else orders['Đã giao'])
        orders['Ngày tạo']=pd.to_datetime(orders['Created Time'].astype(str).str.strip() if 'Created Time' in orders else pd.Series(dtype=str),dayfirst=True,errors='coerce')
        # Order Amount is repeated on multi-line orders; count it only once per Order ID.
        order_level=orders.groupby('Order ID',as_index=False).agg({'Order Amount':'max','Đã hủy':'max','Đã giao':'max','Hợp lệ theo lựa chọn':'max','Ngày tạo':'min'})
        # If a multi-line order contains mixed statuses, avoid treating it as fully retained.
        order_level['Hợp lệ theo lựa chọn']=(~order_level['Đã hủy']) & (True if include_pending else order_level['Đã giao'])
        order_level['Doanh thu giữ lại']=np.where(order_level['Hợp lệ theo lựa chọn'],order_level['Order Amount'],0)

st.subheader('01 / Tổng quan')
spend=float(ov['Chi phí'].sum()) if ov is not None else float(camp['Chi phí'].sum()) if camp is not None else float(prod['Chi phí'].sum()) if prod is not None else np.nan
ads_revenue=float(ov['Doanh thu gộp (Cửa hàng hiện tại)'].sum()) if ov is not None else float(camp['Doanh thu gộp'].sum()) if camp is not None else float(prod['Doanh thu gộp'].sum()) if prod is not None else np.nan
retained=float(order_level['Doanh thu giữ lại'].sum()) if orders is not None else np.nan
cancel_value=float(order_level.loc[order_level['Đã hủy'],'Order Amount'].sum()) if orders is not None else np.nan
cols=st.columns(4)
cols[0].metric('Chi phí Ads',vnd(spend) if pd.notna(spend) else '—')
cols[1].metric('Doanh thu Ads báo cáo',vnd(ads_revenue) if pd.notna(ads_revenue) else '—')
cols[2].metric('ROAS Ads báo cáo',show_roas(ratio(ads_revenue,spend)))
cols[3].metric('ROAS điều chỉnh tham khảo',show_roas(ratio(retained,spend)))
if orders is not None:
    c=st.columns(4)
    c[0].metric('Số đơn (không trùng)',len(order_level))
    c[1].metric('Đơn hủy',int(order_level['Đã hủy'].sum()))
    c[2].metric('Tỷ lệ hủy',f"{order_level['Đã hủy'].mean():.1%}")
    c[3].metric('Giá trị đơn hủy',vnd(cancel_value))
    st.caption(f"Doanh thu đơn hàng theo trạng thái đã chọn: {vnd(retained)}. Tổng giá trị đơn hàng CSV: {vnd(order_level['Order Amount'].sum())}.")
    if pd.notna(ads_revenue):
        delta=ads_revenue-order_level['Order Amount'].sum()
        if abs(delta)>0.01:st.warning(f'Chênh lệch giữa doanh thu Ads và tổng giá trị đơn CSV: {vnd(delta)}. Hai nguồn có thể khác phạm vi, giá trị khuyến mãi hoặc thời điểm ghi nhận. ROAS điều chỉnh là chỉ số THAM KHẢO, không phải ROAS Ads được đối soát theo từng đơn.')
    st.info('Đơn không hủy chưa chắc đã giao/thanh toán thành công. Doanh thu CSV không đồng nghĩa toàn bộ là doanh thu được quy cho Ads. Nếu chưa có mã đơn liên kết với quảng cáo, không thể xác định ROAS Ads sau hủy chính xác.')

if ov is not None:
    st.subheader('02 / Hiệu quả theo ngày')
    day=ov.groupby('Theo ngày',as_index=False)[['Chi phí','Doanh thu gộp (Cửa hàng hiện tại)']].sum().sort_values('Theo ngày')
    day['ROAS']=day.apply(lambda r:ratio(r['Doanh thu gộp (Cửa hàng hiện tại)'],r['Chi phí']),axis=1)
    fig=px.bar(day.melt('Theo ngày',value_vars=['Chi phí','Doanh thu gộp (Cửa hàng hiện tại)'],var_name='Chỉ tiêu',value_name='VND'),x='Theo ngày',y='VND',color='Chỉ tiêu',barmode='group',color_discrete_sequence=['#64748b','#2563eb'])
    fig.update_layout(margin=dict(l=0,r=0,t=10,b=0),legend_title_text='')
    st.plotly_chart(fig,use_container_width=True)
    st.dataframe(day.rename(columns={'Theo ngày':'Ngày','Doanh thu gộp (Cửa hàng hiện tại)':'Doanh thu Ads'}).style.format({'Chi phí':vnd,'Doanh thu Ads':vnd,'ROAS':show_roas}),use_container_width=True,hide_index=True)

if orders is not None:
    st.subheader('03 / Đơn hàng và hủy đơn')
    a,b=st.columns([1,2])
    with a:
        fig=px.pie(names=['Hủy','Không hủy'],values=[int(order_level['Đã hủy'].sum()),int((~order_level['Đã hủy']).sum())],hole=.62,color_discrete_sequence=['#ef4444','#22c55e']);fig.update_layout(margin=dict(l=0,r=0,t=10,b=0));st.plotly_chart(fig,use_container_width=True)
    with b:
        view_cols=[c for c in ['Order ID','Created Time','Product Name','SKU ID','Order Status','Order Substatus','Order Amount','Cancel Reason','Cancellation Reason','Cancelled Time'] if c in orders.columns]
        st.dataframe(orders[view_cols],use_container_width=True,hide_index=True)
    st.download_button('Tải CSV đơn hàng đã chuẩn hóa',orders.to_csv(index=False,encoding='utf-8-sig').encode('utf-8-sig'),file_name='don_hang_chuan_hoa.csv',mime='text/csv')

if camp is not None:
    st.subheader('04 / Chiến dịch GMV Max')
    cv=camp[['ID chiến dịch','Tên chiến dịch','Chi phí','Doanh thu gộp','Số lượng đơn hàng SKU','ROAS tính lại']].copy()
    st.dataframe(cv.style.format({'Chi phí':vnd,'Doanh thu gộp':vnd,'ROAS tính lại':show_roas}),hide_index=True,use_container_width=True)
    fig=px.bar(camp.sort_values('Chi phí',ascending=True),x='Chi phí',y='Tên chiến dịch',orientation='h',color='Doanh thu gộp',color_continuous_scale='Blues');fig.update_layout(height=max(350,len(camp)*48),margin=dict(l=0,r=0,t=15,b=0));st.plotly_chart(fig,use_container_width=True)

if prod is not None:
    st.subheader('05 / Sản phẩm & đối chiếu đơn hủy theo SKU')
    p=prod.copy()
    if orders is not None:
        # SKU-level monetary allocation only safe for single-SKU orders.
        sk=orders.groupby('SKU ID',as_index=False).agg(so_dong=('Order ID','size'),so_don=('Order ID','nunique'),so_don_huy=('Đã hủy','sum'),so_dong_khong_huy=('Hợp lệ theo lựa chọn','sum'))
        p=p.merge(sk,how='left',left_on='ID sản phẩm',right_on='SKU ID')
        p['so_don_huy']=p['so_don_huy'].fillna(0).astype(int)
        p['so_don']=p['so_don'].fillna(0).astype(int)
        p['Đánh giá']=np.select([p['so_don_huy']>0,p['Số lượng đơn hàng SKU']<=0],['Có đơn hủy — cần kiểm tra','Chưa ghi nhận chuyển đổi'],default='Có đơn — kiểm tra lợi nhuận')
    else:p['Đánh giá']=np.where(p['Số lượng đơn hàng SKU']>0,'Có chuyển đổi (chưa đối chiếu hủy)','Chưa ghi nhận chuyển đổi')
    st.dataframe(p[[c for c in ['Tên sản phẩm','ID sản phẩm','Tên chiến dịch','Chi phí','Doanh thu gộp','Số lượng đơn hàng SKU','ROAS tính lại','so_don','so_don_huy','Đánh giá'] if c in p]].style.format({'Chi phí':vnd,'Doanh thu gộp':vnd,'ROAS tính lại':show_roas}),hide_index=True,use_container_width=True)
    if orders is not None:
        missing_sku=set(orders['SKU ID'])-set(prod['ID sản phẩm'])
        if missing_sku:st.warning(f'{len(missing_sku)} SKU trong đơn hàng không khớp ID sản phẩm của báo cáo Ads. Không tự gán theo tên vì có thể sai.')
    st.download_button('Tải bảng đối chiếu sản phẩm',p.to_csv(index=False).encode('utf-8-sig'),file_name='doi_chieu_san_pham.csv',mime='text/csv')

if creative is not None:
    st.subheader('06 / Nội dung quảng cáo')
    types=creative['Loại nội dung sáng tạo'].dropna().unique().tolist() if 'Loại nội dung sáng tạo' in creative else []
    selected=st.multiselect('Loại nội dung',types,default=types)
    cr=creative[creative['Loại nội dung sáng tạo'].isin(selected)].copy() if types else creative.copy()
    if 'Chi phí' in cr:
        cr=cr.sort_values('Chi phí',ascending=False)
        st.metric('Chi phí trong báo cáo Creative (không cộng vào tổng Ads)',vnd(cr['Chi phí'].sum()))
    st.dataframe(cr[[c for c in ['ID bài đăng','Mẫu quảng cáo','Loại nội dung sáng tạo','Chi phí','Doanh thu gộp','Số lượng đơn hàng SKU','Số lượt hiển thị quảng cáo sản phẩm','Số lượt nhấp vào quảng cáo sản phẩm'] if c in cr]].head(100),hide_index=True,use_container_width=True)
    st.caption('Creative có thể ghi nhận doanh thu với chi phí 0đ do phân bổ/ghi nhận của nền tảng. Không xem ROAS cấp Creative là ROAS chiến dịch.')

st.subheader('07 / Kiểm tra chất lượng dữ liệu')
checks=[]
for name,df,sp,rev in [('Campaign overview',ov,'Chi phí','Doanh thu gộp (Cửa hàng hiện tại)'),('Product campaign',camp,'Chi phí','Doanh thu gộp'),('Product data',prod,'Chi phí','Doanh thu gộp'),('Creative data',creative,'Chi phí','Doanh thu gộp')]:
    if df is not None:checks.append({'Nguồn':name,'Số dòng':len(df),'Chi phí':df[sp].sum() if sp in df else np.nan,'Doanh thu':df[rev].sum() if rev in df else np.nan})
if checks:st.dataframe(pd.DataFrame(checks).style.format({'Chi phí':vnd,'Doanh thu':vnd}),use_container_width=True,hide_index=True)
st.caption('Nguồn chuẩn chi phí và doanh thu tổng quan: Campaign overview (nếu có). Các bảng chiến dịch, sản phẩm và Creative dùng để phân tích chi tiết, không cộng dồn. Dữ liệu đơn hàng chỉ tính một lần theo Order ID.')

st.subheader('08 / Ngưỡng ROAS hòa vốn theo từng SKU')
if prod is not None:
    st.caption('Nhập biên đóng góp trước Ads riêng từng SKU (sau giá vốn, phí sàn, voucher, chi phí biến đổi). Không áp dụng một ngưỡng chung.')
    margin_input=prod[['ID sản phẩm','Tên sản phẩm','Chi phí','Doanh thu gộp','ROAS tính lại']].copy()
    margin_input['Biên đóng góp (%)']=np.nan
    edited=st.data_editor(margin_input,hide_index=True,use_container_width=True,disabled=['ID sản phẩm','Tên sản phẩm','Chi phí','Doanh thu gộp','ROAS tính lại'],column_config={'Biên đóng góp (%)':st.column_config.NumberColumn('Biên đóng góp (%)',min_value=0.01,max_value=100,step=1,help='Ví dụ: 30 nghĩa là 30%')},key='margin_editor')
    edited['ROAS hòa vốn']=edited['Biên đóng góp (%)'].apply(lambda x:100/x if pd.notna(x) and x>0 else np.nan)
    edited['So với hòa vốn']=edited.apply(lambda r:'Chưa đủ dữ liệu' if pd.isna(r['ROAS hòa vốn']) else ('Đạt ngưỡng' if pd.notna(r['ROAS tính lại']) and r['ROAS tính lại']>=r['ROAS hòa vốn'] else 'Dưới ngưỡng'),axis=1)
    st.dataframe(edited[['Tên sản phẩm','ROAS tính lại','Biên đóng góp (%)','ROAS hòa vốn','So với hòa vốn']].style.format({'ROAS tính lại':show_roas,'ROAS hòa vốn':show_roas}),hide_index=True,use_container_width=True)
else:st.caption('Tải Product data để nhập ngưỡng ROAS riêng cho từng sản phẩm.')
