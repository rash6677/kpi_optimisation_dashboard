
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import numpy as np
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(
    page_title="Meesho Business Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

# Load data
@st.cache_data
def load_data():
    conn = sqlite3.connect('meesho_analytics.db')
    df = pd.read_sql_query("SELECT * FROM orders", conn)
    df['order_date'] = pd.to_datetime(df['order_date'])
    conn.close()
    return df

df = load_data()

# Sidebar filters
st.sidebar.header("Filters")
date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(df['order_date'].min(), df['order_date'].max()),
    min_value=df['order_date'].min(),
    max_value=df['order_date'].max()
)

categories = st.sidebar.multiselect(
    "Select Categories",
    options=df['product_category'].unique(),
    default=df['product_category'].unique()
)

cities = st.sidebar.multiselect(
    "Select Cities",
    options=df['customer_city'].unique(),
    default=df['customer_city'].unique()
)

# Filter data
filtered_df = df[
    (df['order_date'].dt.date >= date_range[0]) &
    (df['order_date'].dt.date <= date_range[1]) &
    (df['product_category'].isin(categories)) &
    (df['customer_city'].isin(cities))
]

# Main dashboard
st.title(" E-Commerce Business Analytics Dashboard")
st.markdown("---")

# KPI Metrics Row
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    total_revenue = filtered_df['final_price'].sum()
    st.metric("Total Revenue", f"₹{total_revenue:,.0f}")

with col2:
    total_orders = len(filtered_df)
    st.metric("Total Orders", f"{total_orders:,}")

with col3:
    aov = filtered_df['final_price'].mean()
    st.metric("Average Order Value", f"₹{aov:.0f}")

with col4:
    unique_customers = filtered_df['customer_id'].nunique()
    st.metric("Unique Customers", f"{unique_customers:,}")

with col5:
    repeat_rate = (filtered_df.groupby('customer_id').size() > 1).mean() * 100
    st.metric("Repeat Customer Rate", f"{repeat_rate:.1f}%")

st.markdown("---")

# Charts Row 1
col1, col2 = st.columns(2)

with col1:
    # Monthly Revenue Trend
    monthly_revenue = filtered_df.groupby(filtered_df['order_date'].dt.to_period('M')).agg({
        'final_price': 'sum',
        'order_id': 'count'
    }).reset_index()
    monthly_revenue['order_date'] = monthly_revenue['order_date'].astype(str)
    
    fig_monthly = px.line(monthly_revenue, x='order_date', y='final_price',
                         title='Monthly Revenue Trend',
                         labels={'final_price': 'Revenue (₹)', 'order_date': 'Month'})
    fig_monthly.update_layout(showlegend=False)
    st.plotly_chart(fig_monthly, use_container_width=True)

with col2:
    # Category Performance
    category_revenue = filtered_df.groupby('product_category')['final_price'].sum().sort_values(ascending=True)
    
    fig_category = px.bar(x=category_revenue.values, y=category_revenue.index,
                         orientation='h',
                         title='Revenue by Category',
                         labels={'x': 'Revenue (₹)', 'y': 'Category'})
    fig_category.update_layout(showlegend=False)
    st.plotly_chart(fig_category, use_container_width=True)

# Charts Row 2
col1, col2 = st.columns(2)

with col1:
    # City Performance
    city_performance = filtered_df.groupby('customer_city').agg({
        'final_price': 'sum',
        'customer_id': 'nunique'
    }).sort_values('final_price', ascending=False).head(8)
    
    fig_city = px.scatter(city_performance, x='customer_id', y='final_price',
                         hover_data=['final_price'],
                         title='City Performance: Revenue vs Customers',
                         labels={'customer_id': 'Unique Customers', 'final_price': 'Revenue (₹)'})
    
    for i, city in enumerate(city_performance.index):
        fig_city.add_annotation(
            x=city_performance.loc[city, 'customer_id'],
            y=city_performance.loc[city, 'final_price'],
            text=city,
            showarrow=True,
            arrowhead=2
        )
    
    st.plotly_chart(fig_city, use_container_width=True)

with col2:
    # Payment Method Distribution
    payment_dist = filtered_df['payment_method'].value_counts()
    
    fig_payment = px.pie(values=payment_dist.values, names=payment_dist.index,
                        title='Payment Method Distribution')
    st.plotly_chart(fig_payment, use_container_width=True)

# Detailed Analysis Section
st.markdown("---")
st.header("📈 Detailed Analysis")

tab1, tab2, tab3 = st.tabs(["Customer Segmentation", "Product Analysis", "Time Analysis"])

with tab1:
    # Customer Segmentation
    customer_metrics = filtered_df.groupby('customer_id').agg({
        'final_price': ['sum', 'count', 'mean'],
        'order_date': 'max'
    }).round(2)
    
    customer_metrics.columns = ['total_spent', 'order_count', 'avg_order_value', 'last_order']
    customer_metrics['days_since_last_order'] = (datetime.now() - pd.to_datetime(customer_metrics['last_order'])).dt.days
    
    # Segmentation logic
    def segment_customers(row):
        if row['total_spent'] >= 5000 and row['order_count'] >= 5:
            return 'High Value'
        elif row['total_spent'] >= 2000 and row['order_count'] >= 3:
            return 'Medium Value'
        elif row['days_since_last_order'] <= 30:
            return 'Recent Active'
        elif row['days_since_last_order'] > 90:
            return 'At Risk'
        else:
            return 'Regular'
    
    customer_metrics['segment'] = customer_metrics.apply(segment_customers, axis=1)
    segment_summary = customer_metrics.groupby('segment').agg({
        'total_spent': ['count', 'mean'],
        'order_count': 'mean',
        'avg_order_value': 'mean'
    }).round(2)
    
    st.subheader("Customer Segmentation Analysis")
    st.dataframe(segment_summary)
    
    # Segment distribution pie chart
    segment_dist = customer_metrics['segment'].value_counts()
    fig_segments = px.pie(values=segment_dist.values, names=segment_dist.index,
                         title='Customer Segment Distribution')
    st.plotly_chart(fig_segments, use_container_width=True)

with tab2:
    # Product Analysis
    st.subheader("Product Category Performance")
    
    product_analysis = filtered_df.groupby('product_category').agg({
        'final_price': ['sum', 'count', 'mean'],
        'discount_percent': 'mean',
        'customer_id': 'nunique'
    }).round(2)
    
    product_analysis.columns = ['total_revenue', 'total_orders', 'avg_order_value', 'avg_discount', 'unique_customers']
    product_analysis['revenue_per_customer'] = (product_analysis['total_revenue'] / product_analysis['unique_customers']).round(2)
    
    st.dataframe(product_analysis.sort_values('total_revenue', ascending=False))
    
    # Discount vs Revenue analysis
    fig_discount = px.scatter(product_analysis, x='avg_discount', y='total_revenue',
                             size='total_orders', hover_name=product_analysis.index,
                             title='Discount Rate vs Revenue by Category')
    st.plotly_chart(fig_discount, use_container_width=True)

with tab3:
    # Time Analysis
    st.subheader("Time-based Analysis")
    
    # Weekday performance
    filtered_df['weekday'] = filtered_df['order_date'].dt.day_name()
    weekday_performance = filtered_df.groupby('weekday').agg({
        'final_price': ['sum', 'count', 'mean']
    }).round(2)
    weekday_performance.columns = ['total_revenue', 'total_orders', 'avg_order_value']
    
    # Reorder by weekday
    weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    weekday_performance = weekday_performance.reindex(weekday_order)
    
    fig_weekday = px.bar(weekday_performance, x=weekday_performance.index, y='total_revenue',
                        title='Revenue by Day of Week')
    st.plotly_chart(fig_weekday, use_container_width=True)
    
    # Hour analysis (if hour data available)
    if 'order_hour' in filtered_df.columns:
        hourly_orders = filtered_df.groupby('order_hour')['final_price'].sum()
        fig_hourly = px.line(x=hourly_orders.index, y=hourly_orders.values,
                           title='Revenue by Hour of Day')
        st.plotly_chart(fig_hourly, use_container_width=True)

# Insights and Recommendations
st.markdown("---")
st.header("💡 Key Insights & Recommendations")

insights = [
    f"📊 **Revenue Performance**: Total revenue of ₹{total_revenue:,.0f} from {total_orders:,} orders",
    f"💰 **Customer Value**: Average order value is ₹{aov:.0f} with {repeat_rate:.1f}% repeat customers",
    f"🏆 **Top Category**: {category_revenue.index[-1]} generates highest revenue",
    f"🎯 **Growth Opportunity**: Focus on customer retention to improve repeat rate",
    f"📈 **Recommendation**: Implement targeted campaigns for 'At Risk' customer segment"
]

for insight in insights:
    st.markdown(insight)

# Footer
st.markdown("---")
st.markdown("*Dashboard created for Meesho Business Analyst Role - Data-driven insights for business growth*")
