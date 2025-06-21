"""
Advanced Reporting and Analytics System
Generates Excel and PDF reports with visualizations
"""

import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import io
import base64
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
import plotly.graph_objects as go
import plotly.express as px
from plotly.offline import plot
import json
from pathlib import Path

class ReportGenerator:
    def __init__(self, db_path: str = "inferno_documents.db"):
        self.db_path = db_path
        # Set matplotlib style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
    
    def get_analytics_data(self) -> dict:
        """Get comprehensive analytics data from database"""
        conn = sqlite3.connect(self.db_path)
        
        try:
            # Basic document statistics
            documents_df = pd.read_sql_query("""
                SELECT d.document_id, d.file_path, d.document_type, d.sub_category,
                       d.processing_status, d.created_at, d.file_size, d.file_format,
                       p.primary_name as uploader_name, p.nationality, p.gender
                FROM documents d
                LEFT JOIN person_documents pd ON d.document_id = pd.document_id
                LEFT JOIN persons p ON pd.person_hash = p.person_hash
            """, conn)
            
            # Document fields data
            fields_df = pd.read_sql_query("""
                SELECT document_id, field_name, field_value
                FROM document_fields
            """, conn)
            
            # Processing statistics
            processing_stats = pd.read_sql_query("""
                SELECT processing_status, COUNT(*) as count
                FROM documents
                GROUP BY processing_status
            """, conn)
            
            return {
                'documents': documents_df,
                'fields': fields_df,
                'processing_stats': processing_stats
            }
            
        finally:
            conn.close()
    
    def generate_excel_report(self) -> io.BytesIO:
        """Generate comprehensive Excel report"""
        data = self.get_analytics_data()
        documents_df = data['documents']
        
        # Create Excel buffer
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Summary sheet
            summary_data = {
                'Metric': [
                    'Total Documents',
                    'Unique Users',
                    'Total File Size (MB)',
                    'Average File Size (KB)',
                    'Largest File (MB)',
                    'Most Common Document Type',
                    'Processing Success Rate (%)',
                    'Documents Needing Review'
                ],
                'Value': [
                    len(documents_df),
                    documents_df['uploader_name'].nunique(),
                    round(documents_df['file_size'].sum() / (1024*1024), 2),
                    round(documents_df['file_size'].mean() / 1024, 2),
                    round(documents_df['file_size'].max() / (1024*1024), 2),
                    documents_df['document_type'].mode().iloc[0] if not documents_df.empty else 'N/A',
                    round((documents_df['processing_status'] == 'processed').mean() * 100, 1),
                    len(documents_df[documents_df['processing_status'].isin(['needs_review', 'error'])])
                ]
            }
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Documents detail sheet
            detail_df = documents_df.copy()
            detail_df['file_name'] = detail_df['file_path'].apply(lambda x: Path(x).name if pd.notna(x) else 'Unknown')
            detail_df['file_size_mb'] = detail_df['file_size'] / (1024*1024)
            detail_df['upload_date'] = pd.to_datetime(detail_df['created_at']).dt.date
            
            columns_to_export = [
                'file_name', 'document_type', 'sub_category', 'uploader_name', 
                'file_size_mb', 'file_format', 'processing_status', 'upload_date'
            ]
            
            detail_df[columns_to_export].to_excel(writer, sheet_name='Documents', index=False)
            
            # Documents by user
            user_stats = documents_df.groupby('uploader_name').agg({
                'document_id': 'count',
                'file_size': ['sum', 'mean', 'max'],
                'created_at': ['min', 'max']
            }).round(2)
            
            user_stats.columns = ['Document_Count', 'Total_Size_Bytes', 'Avg_Size_Bytes', 'Max_Size_Bytes', 'First_Upload', 'Last_Upload']
            user_stats['Total_Size_MB'] = user_stats['Total_Size_Bytes'] / (1024*1024)
            user_stats.to_excel(writer, sheet_name='Users')
            
            # Document types breakdown
            type_stats = documents_df.groupby('document_type').agg({
                'document_id': 'count',
                'file_size': 'sum',
                'processing_status': lambda x: (x == 'processed').mean() * 100
            }).round(2)
            
            type_stats.columns = ['Count', 'Total_Size_Bytes', 'Success_Rate_Percent']
            type_stats['Total_Size_MB'] = type_stats['Total_Size_Bytes'] / (1024*1024)
            type_stats.to_excel(writer, sheet_name='Document_Types')
            
            # Processing status breakdown
            status_stats = documents_df['processing_status'].value_counts().to_frame()
            status_stats.columns = ['Count']
            status_stats['Percentage'] = (status_stats['Count'] / len(documents_df) * 100).round(1)
            status_stats.to_excel(writer, sheet_name='Processing_Status')
            
            # Time-based analysis (if we have enough data)
            if len(documents_df) > 0:
                documents_df['upload_date'] = pd.to_datetime(documents_df['created_at']).dt.date
                daily_uploads = documents_df.groupby('upload_date').size().to_frame()
                daily_uploads.columns = ['Upload_Count']
                daily_uploads.to_excel(writer, sheet_name='Daily_Uploads')
        
        output.seek(0)
        return output
    
    def generate_pdf_report(self) -> io.BytesIO:
        """Generate PDF report with visualizations"""
        data = self.get_analytics_data()
        documents_df = data['documents']
        
        # Create PDF buffer
        output = io.BytesIO()
        
        with PdfPages(output) as pdf:
            # Page 1: Overview
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle('Document Management Dashboard - Analytics Report', fontsize=16, fontweight='bold')
            
            # Document types pie chart
            type_counts = documents_df['document_type'].value_counts()
            ax1.pie(type_counts.values, labels=type_counts.index, autopct='%1.1f%%', startangle=90)
            ax1.set_title('Document Types Distribution')
            
            # Processing status bar chart
            status_counts = documents_df['processing_status'].value_counts()
            bars = ax2.bar(status_counts.index, status_counts.values)
            ax2.set_title('Processing Status')
            ax2.set_ylabel('Count')
            ax2.tick_params(axis='x', rotation=45)
            
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}', ha='center', va='bottom')
            
            # File size distribution
            file_sizes_mb = documents_df['file_size'] / (1024*1024)
            ax3.hist(file_sizes_mb, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
            ax3.set_title('File Size Distribution')
            ax3.set_xlabel('File Size (MB)')
            ax3.set_ylabel('Frequency')
            
            # Uploads per user
            user_counts = documents_df['uploader_name'].value_counts().head(10)
            bars = ax4.barh(range(len(user_counts)), user_counts.values)
            ax4.set_yticks(range(len(user_counts)))
            ax4.set_yticklabels(user_counts.index)
            ax4.set_title('Top 10 Users by Upload Count')
            ax4.set_xlabel('Number of Documents')
            
            # Add value labels
            for i, bar in enumerate(bars):
                width = bar.get_width()
                ax4.text(width, bar.get_y() + bar.get_height()/2.,
                        f'{int(width)}', ha='left', va='center')
            
            plt.tight_layout()
            pdf.savefig(fig, bbox_inches='tight')
            plt.close()
            
            # Page 2: Time-based analysis
            if len(documents_df) > 0:
                fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12))
                fig.suptitle('Time-based Analysis', fontsize=16, fontweight='bold')
                
                # Uploads over time
                documents_df['upload_date'] = pd.to_datetime(documents_df['created_at']).dt.date
                daily_uploads = documents_df.groupby('upload_date').size()
                
                ax1.plot(daily_uploads.index, daily_uploads.values, marker='o', linewidth=2, markersize=6)
                ax1.set_title('Daily Upload Trends')
                ax1.set_xlabel('Date')
                ax1.set_ylabel('Number of Uploads')
                ax1.grid(True, alpha=0.3)
                
                # Monthly summary (if we have enough data)
                if len(daily_uploads) > 30:
                    documents_df['upload_month'] = pd.to_datetime(documents_df['created_at']).dt.to_period('M')
                    monthly_uploads = documents_df.groupby('upload_month').size()
                    
                    ax2.bar(range(len(monthly_uploads)), monthly_uploads.values, alpha=0.7)
                    ax2.set_xticks(range(len(monthly_uploads)))
                    ax2.set_xticklabels([str(month) for month in monthly_uploads.index], rotation=45)
                    ax2.set_title('Monthly Upload Summary')
                    ax2.set_ylabel('Number of Uploads')
                    
                    # Add value labels
                    for i, v in enumerate(monthly_uploads.values):
                        ax2.text(i, v, str(v), ha='center', va='bottom')
                else:
                    # Show hourly distribution instead
                    documents_df['upload_hour'] = pd.to_datetime(documents_df['created_at']).dt.hour
                    hourly_uploads = documents_df.groupby('upload_hour').size()
                    
                    ax2.bar(hourly_uploads.index, hourly_uploads.values, alpha=0.7)
                    ax2.set_title('Upload Distribution by Hour of Day')
                    ax2.set_xlabel('Hour (24h format)')
                    ax2.set_ylabel('Number of Uploads')
                
                plt.tight_layout()
                pdf.savefig(fig, bbox_inches='tight')
                plt.close()
            
            # Page 3: Quality metrics
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle('Document Quality and Processing Metrics', fontsize=16, fontweight='bold')
            
            # Success rate by document type
            type_success = documents_df.groupby('document_type')['processing_status'].apply(
                lambda x: (x == 'processed').mean() * 100
            ).sort_values(ascending=True)
            
            bars = ax1.barh(range(len(type_success)), type_success.values)
            ax1.set_yticks(range(len(type_success)))
            ax1.set_yticklabels(type_success.index)
            ax1.set_title('Processing Success Rate by Document Type')
            ax1.set_xlabel('Success Rate (%)')
            
            # Add value labels
            for i, bar in enumerate(bars):
                width = bar.get_width()
                ax1.text(width, bar.get_y() + bar.get_height()/2.,
                        f'{width:.1f}%', ha='left', va='center')
            
            # File format distribution
            format_counts = documents_df['file_format'].value_counts()
            ax2.pie(format_counts.values, labels=format_counts.index, autopct='%1.1f%%')
            ax2.set_title('File Format Distribution')
            
            # Average file size by type
            type_avg_size = documents_df.groupby('document_type')['file_size'].mean() / (1024*1024)
            bars = ax3.bar(type_avg_size.index, type_avg_size.values)
            ax3.set_title('Average File Size by Document Type')
            ax3.set_ylabel('Average Size (MB)')
            ax3.tick_params(axis='x', rotation=45)
            
            # User activity levels
            user_activity = documents_df['uploader_name'].value_counts()
            activity_levels = pd.cut(user_activity.values, bins=[0, 1, 5, 10, float('inf')], 
                                   labels=['1 doc', '2-5 docs', '6-10 docs', '10+ docs'])
            activity_counts = activity_levels.value_counts()
            
            ax4.pie(activity_counts.values, labels=activity_counts.index, autopct='%1.1f%%')
            ax4.set_title('User Activity Levels')
            
            plt.tight_layout()
            pdf.savefig(fig, bbox_inches='tight')
            plt.close()
        
        output.seek(0)
        return output
    
    def generate_interactive_dashboard_data(self) -> dict:
        """Generate data for interactive web dashboard"""
        data = self.get_analytics_data()
        documents_df = data['documents']
        
        # Document types chart
        type_counts = documents_df['document_type'].value_counts()
        types_chart = {
            'labels': type_counts.index.tolist(),
            'data': type_counts.values.tolist(),
            'colors': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40']
        }
        
        # Processing status chart
        status_counts = documents_df['processing_status'].value_counts()
        status_chart = {
            'labels': status_counts.index.tolist(),
            'data': status_counts.values.tolist()
        }
        
        # Uploads over time
        documents_df['upload_date'] = pd.to_datetime(documents_df['created_at']).dt.date
        daily_uploads = documents_df.groupby('upload_date').size()
        
        uploads_timeline = {
            'dates': [str(date) for date in daily_uploads.index],
            'counts': daily_uploads.values.tolist()
        }
        
        # User statistics
        user_stats = documents_df.groupby('uploader_name').agg({
            'document_id': 'count',
            'file_size': 'sum'
        }).sort_values('document_id', ascending=False).head(10)
        
        top_users = {
            'users': user_stats.index.tolist(),
            'document_counts': user_stats['document_id'].tolist(),
            'total_sizes': (user_stats['file_size'] / (1024*1024)).round(2).tolist()
        }
        
        # Summary statistics
        summary_stats = {
            'total_documents': len(documents_df),
            'total_users': documents_df['uploader_name'].nunique(),
            'total_size_mb': round(documents_df['file_size'].sum() / (1024*1024), 2),
            'avg_size_kb': round(documents_df['file_size'].mean() / 1024, 2),
            'success_rate': round((documents_df['processing_status'] == 'processed').mean() * 100, 1),
            'needs_review': len(documents_df[documents_df['processing_status'].isin(['needs_review', 'error'])])
        }
        
        return {
            'summary': summary_stats,
            'document_types': types_chart,
            'processing_status': status_chart,
            'uploads_timeline': uploads_timeline,
            'top_users': top_users
        }


class AdvancedAnalytics:
    """Advanced analytics and insights"""
    
    def __init__(self, db_path: str = "inferno_documents.db"):
        self.db_path = db_path
    
    def get_processing_insights(self) -> dict:
        """Get insights about processing patterns and quality"""
        conn = sqlite3.connect(self.db_path)
        
        try:
            # Get documents with field completeness
            query = """
                SELECT d.document_id, d.document_type, d.processing_status,
                       COUNT(df.field_name) as total_fields,
                       SUM(CASE WHEN df.field_value IN ('N/A', '', 'Unknown', 'None') THEN 1 ELSE 0 END) as empty_fields
                FROM documents d
                LEFT JOIN document_fields df ON d.document_id = df.document_id
                GROUP BY d.document_id
            """
            
            completeness_df = pd.read_sql_query(query, conn)
            completeness_df['completion_rate'] = (
                (completeness_df['total_fields'] - completeness_df['empty_fields']) / 
                completeness_df['total_fields'] * 100
            ).fillna(0)
            
            insights = {
                'overall_completion_rate': completeness_df['completion_rate'].mean(),
                'documents_needing_review': len(completeness_df[completeness_df['completion_rate'] < 70]),
                'completion_by_type': completeness_df.groupby('document_type')['completion_rate'].mean().to_dict(),
                'processing_success_rate': (completeness_df['processing_status'] == 'processed').mean() * 100
            }
            
            return insights
            
        finally:
            conn.close()
    
    def suggest_improvements(self) -> list:
        """Suggest system improvements based on data analysis"""
        insights = self.get_processing_insights()
        suggestions = []
        
        if insights['overall_completion_rate'] < 80:
            suggestions.append({
                'type': 'processing_quality',
                'priority': 'high',
                'suggestion': 'Consider improving OCR quality or adding more specific extraction rules',
                'metric': f"Overall completion rate: {insights['overall_completion_rate']:.1f}%"
            })
        
        if insights['documents_needing_review'] > 10:
            suggestions.append({
                'type': 'workflow',
                'priority': 'medium',
                'suggestion': 'Implement automated pre-screening to identify documents needing manual review',
                'metric': f"{insights['documents_needing_review']} documents need review"
            })
        
        # Check for document types with low success rates
        for doc_type, completion in insights['completion_by_type'].items():
            if completion < 60:
                suggestions.append({
                    'type': 'document_specific',
                    'priority': 'medium',
                    'suggestion': f'Improve processing for {doc_type} documents',
                    'metric': f"{doc_type}: {completion:.1f}% completion rate"
                })
        
        return suggestions
