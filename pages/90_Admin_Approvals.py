# pages/90_Admin_Approvals.py
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st
from supabase import create_client

from core.supabase_client import supa_service
from core.auth import provision_user_for_access_request, reset_password_and_resend

st.set_page_config(
    page_title="Admin Approvals - ONACC",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Styles CSS ultra-modernes ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        
        * {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        /* Header avec gradient */
        .admin-header {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            padding: 2rem;
            border-radius: 16px;
            margin-bottom: 2rem;
            color: white;
            box-shadow: 0 10px 40px rgba(245, 87, 108, 0.3);
        }
        
        .admin-title {
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 0.5rem;
            letter-spacing: -0.5px;
        }
        
        .admin-subtitle {
            font-size: 1.1rem;
            opacity: 0.95;
            font-weight: 400;
        }
        
        /* Stats cards */
        .stats-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
            border-left: 4px solid #f5576c;
            transition: all 0.3s ease;
        }
        
        .stats-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 25px rgba(245, 87, 108, 0.15);
        }
        
        .stats-number {
            font-size: 2.5rem;
            font-weight: 800;
            color: #f5576c;
            margin-bottom: 0.3rem;
        }
        
        .stats-label {
            font-size: 0.95rem;
            color: #666;
            font-weight: 500;
        }
        
        /* Request card (liste) */
        .request-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            margin-bottom: 1rem;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06);
            border-left: 4px solid #f093fb;
            transition: all 0.3s ease;
            cursor: pointer;
        }
        
        .request-card:hover {
            transform: translateX(4px);
            box-shadow: 0 4px 20px rgba(240, 147, 251, 0.2);
        }
        
        .request-card-selected {
            border-left-color: #f5576c;
            background: linear-gradient(135deg, rgba(240, 147, 251, 0.05) 0%, rgba(245, 87, 108, 0.05) 100%);
        }
        
        .request-name {
            font-size: 1.2rem;
            font-weight: 700;
            color: #1a1a1a;
            margin-bottom: 0.3rem;
        }
        
        .request-email {
            font-size: 0.95rem;
            color: #666;
            margin-bottom: 0.5rem;
        }
        
        .request-meta {
            font-size: 0.85rem;
            color: #999;
        }
        
        .role-badge {
            display: inline-block;
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            background: #e3f2fd;
            color: #1976d2;
            margin-left: 0.5rem;
        }
        
        /* Detail card */
        .detail-card {
            background: white;
            padding: 2rem;
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            margin-bottom: 1.5rem;
        }
        
        .detail-section {
            margin-bottom: 1.5rem;
        }
        
        .detail-label {
            font-size: 0.85rem;
            color: #999;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.3rem;
            font-weight: 600;
        }
        
        .detail-value {
            font-size: 1.1rem;
            color: #1a1a1a;
            font-weight: 500;
        }
        
        /* Action buttons */
        .action-btn-approve {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: white;
            padding: 1rem 2rem;
            border-radius: 10px;
            font-weight: 700;
            border: none;
            box-shadow: 0 4px 15px rgba(17, 153, 142, 0.3);
            transition: all 0.3s ease;
            cursor: pointer;
        }
        
        .action-btn-approve:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(17, 153, 142, 0.4);
        }
        
        .action-btn-resend {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem 2rem;
            border-radius: 10px;
            font-weight: 700;
            border: none;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            transition: all 0.3s ease;
            cursor: pointer;
        }
        
        .action-btn-resend:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }
        
        /* Status indicators */
        .status-pending {
            display: inline-block;
            padding: 0.4rem 1rem;
            border-radius: 20px;
            background: #fff3cd;
            color: #856404;
            font-size: 0.9rem;
            font-weight: 600;
        }
        
        .status-approved {
            display: inline-block;
            padding: 0.4rem 1rem;
            border-radius: 20px;
            background: #d4edda;
            color: #155724;
            font-size: 0.9rem;
            font-weight: 600;
        }
        
        .status-error {
            display: inline-block;
            padding: 0.4rem 1rem;
            border-radius: 20px;
            background: #f8d7da;
            color: #721c24;
            font-size: 0.9rem;
            font-weight: 600;
        }
        
        /* Timeline */
        .timeline-item {
            padding-left: 2rem;
            border-left: 2px solid #e0e0e0;
            margin-bottom: 1rem;
            position: relative;
        }
        
        .timeline-item::before {
            content: '';
            position: absolute;
            left: -6px;
            top: 0;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #f5576c;
        }
        
        .timeline-date {
            font-size: 0.85rem;
            color: #999;
            margin-bottom: 0.3rem;
        }
        
        .timeline-content {
            font-size: 0.95rem;
            color: #333;
        }
        
        /* Info boxes */
        .info-box {
            background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
            border-left: 4px solid #2196F3;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            margin: 1rem 0;
        }
        
        .warning-box {
            background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
            border-left: 4px solid #ff9800;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            margin: 1rem 0;
        }
        
        .success-box {
            background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
            border-left: 4px solid #4caf50;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            margin: 1rem 0;
        }
        
        .error-box {
            background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
            border-left: 4px solid #f44336;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            margin: 1rem 0;
        }
        
        /* Custom divider */
        .custom-divider {
            height: 2px;
            background: linear-gradient(90deg, transparent, #f5576c, transparent);
            margin: 2rem 0;
            border: none;
        }
        
        /* Empty state */
        .empty-state {
            text-align: center;
            padding: 3rem;
            color: #999;
        }
        
        .empty-state-icon {
            font-size: 4rem;
            margin-bottom: 1rem;
        }
        
        /* Animation */
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .animate-in {
            animation: fadeIn 0.5s ease-out;
        }
    </style>
""", unsafe_allow_html=True)

SUPER_ADMINS = set((st.secrets.get("SUPER_ADMIN_EMAILS") or []))

def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

@st.cache_resource(show_spinner=False)
def user_client_cached():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])

def attach_user_session(c):
    token = st.session_state.get("access_token")
    refresh = st.session_state.get("refresh_token")
    if not token or not refresh:
        return False
    c.auth.set_session(token, refresh)
    try:
        c.postgrest.auth(token)
    except Exception:
        pass
    return True

def current_email(c) -> str:
    try:
        u = c.auth.get_user()
        if hasattr(u, "user") and getattr(u.user, "email", None):
            return str(u.user.email).lower()
        if isinstance(u, dict):
            return str((u.get("user") or {}).get("email", "")).lower()
    except Exception:
        return ""
    return ""

# --- Header personnalisé ---
st.markdown("""
    <div class="admin-header animate-in">
        <div class="admin-title">✅ Gestion des Approbations</div>
        <div class="admin-subtitle">
            Administration des demandes d'accès à la plateforme ONACC Climate Risk
        </div>
    </div>
""", unsafe_allow_html=True)

# --- Auth guard ---
uc = user_client_cached()
if not attach_user_session(uc):
    st.warning("⚠️ Veuillez vous connecter pour accéder à cette page.")
    if st.button("🔐 Se connecter", type="primary"):
        st.switch_page("pages/02_Connexion.py")
    st.stop()

me = current_email(uc)
if not me:
    st.error("❌ Session invalide. Veuillez vous reconnecter.")
    if st.button("🔐 Se reconnecter", type="primary"):
        st.switch_page("pages/02_Connexion.py")
    st.stop()

if me not in SUPER_ADMINS:
    st.error("🚫 Accès refusé. Rôle super_admin requis.")
    st.info("Cette page est réservée aux super-administrateurs de la plateforme.")
    st.stop()

svc = supa_service()

# --- Statistiques globales ---
st.markdown("### 📊 Vue d'ensemble des demandes")

all_requests = svc.table("access_requests").select("id,status").execute().data or []
pending_count = len([r for r in all_requests if r.get("status") == "pending"])
approved_count = len([r for r in all_requests if r.get("status") == "approved"])
rejected_count = len([r for r in all_requests if r.get("status") == "rejected"])
total_count = len(all_requests)

stats_cols = st.columns(4)

with stats_cols[0]:
    st.markdown(f"""
        <div class="stats-card">
            <div class="stats-number">{total_count}</div>
            <div class="stats-label">📋 Total demandes</div>
        </div>
    """, unsafe_allow_html=True)

with stats_cols[1]:
    st.markdown(f"""
        <div class="stats-card" style="border-left-color: #ff9800;">
            <div class="stats-number" style="color: #ff9800;">{pending_count}</div>
            <div class="stats-label">⏳ En attente</div>
        </div>
    """, unsafe_allow_html=True)

with stats_cols[2]:
    st.markdown(f"""
        <div class="stats-card" style="border-left-color: #4caf50;">
            <div class="stats-number" style="color: #4caf50;">{approved_count}</div>
            <div class="stats-label">✅ Approuvées</div>
        </div>
    """, unsafe_allow_html=True)

with stats_cols[3]:
    st.markdown(f"""
        <div class="stats-card" style="border-left-color: #f44336;">
            <div class="stats-number" style="color: #f44336;">{rejected_count}</div>
            <div class="stats-label">❌ Rejetées</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

# --- Pending list ---
pending = (
    svc.table("access_requests")
    .select(
        "id,fullname,email,org,phone,requested_role,status,created_at,"
        "provisioned_user_id,temp_password_sent_at,last_error,provision_error"
    )
    .eq("status", "pending")
    .order("created_at", desc=True)
    .execute()
    .data
) or []

if not pending:
    st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">📭</div>
            <h3>Aucune demande en attente</h3>
            <p>Toutes les demandes d'accès ont été traitées.</p>
        </div>
    """, unsafe_allow_html=True)
    st.stop()

# --- Liste et détails ---
st.markdown(f"### 📋 Demandes en attente ({len(pending)})")

col_list, col_detail = st.columns([1, 2])

with col_list:
    st.markdown("#### 📌 Liste des demandes")
    
    # Utiliser un selectbox plus visuel
    if "selected_request_idx" not in st.session_state:
        st.session_state.selected_request_idx = 0
    
    for idx, req in enumerate(pending):
        created_date = req.get("created_at", "")[:10] if req.get("created_at") else "N/A"
        
        card_class = "request-card"
        if idx == st.session_state.selected_request_idx:
            card_class += " request-card-selected"
        
        if st.button(
            f"{req.get('fullname', 'N/A')}",
            key=f"select_req_{idx}",
            use_container_width=True,
            type="secondary" if idx != st.session_state.selected_request_idx else "primary"
        ):
            st.session_state.selected_request_idx = idx
            st.rerun()
        
        st.caption(f"📧 {req.get('email', 'N/A')} • 📅 {created_date}")
        if idx < len(pending) - 1:
            st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.2;'>", unsafe_allow_html=True)

with col_detail:
    req = pending[st.session_state.selected_request_idx]
    
    st.markdown("#### 👤 Détails de la demande")
    
    # Card principal avec infos
    st.markdown(f"""
        <div class="detail-card">
            <div class="detail-section">
                <div class="detail-label">Nom complet</div>
                <div class="detail-value">👤 {req.get('fullname', 'N/A')}</div>
            </div>
            
            <div class="detail-section">
                <div class="detail-label">Email</div>
                <div class="detail-value">📧 {req.get('email', 'N/A')}</div>
            </div>
            
            <div class="detail-section">
                <div class="detail-label">Organisation</div>
                <div class="detail-value">🏢 {req.get('org', 'N/A')}</div>
            </div>
            
            <div class="detail-section">
                <div class="detail-label">Téléphone</div>
                <div class="detail-value">📱 {req.get('phone', 'Non renseigné')}</div>
            </div>
            
            <div class="detail-section">
                <div class="detail-label">Rôle demandé</div>
                <div class="detail-value">
                    <span class="role-badge">{req.get('requested_role', 'N/A')}</span>
                </div>
            </div>
            
            <div class="detail-section">
                <div class="detail-label">Date de demande</div>
                <div class="detail-value">📅 {req.get('created_at', 'N/A')[:19] if req.get('created_at') else 'N/A'}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Statut provisioning
    if req.get("provisioned_user_id"):
        st.markdown("""
            <div class="success-box">
                ✅ <strong>Compte utilisateur créé</strong><br>
                Un compte a déjà été provisionné pour cette demande.
            </div>
        """, unsafe_allow_html=True)
    
    if req.get("temp_password_sent_at"):
        st.markdown(f"""
            <div class="info-box">
                📧 <strong>Email envoyé</strong><br>
                Identifiants envoyés le {req.get('temp_password_sent_at', 'N/A')[:19]}
            </div>
        """, unsafe_allow_html=True)
    
    if req.get("provision_error") or req.get("last_error"):
        error_msg = req.get("provision_error") or req.get("last_error")
        st.markdown(f"""
            <div class="error-box">
                ⚠️ <strong>Erreur détectée</strong><br>
                {error_msg}
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Actions
    st.markdown("#### ⚡ Actions disponibles")
    
    action_col1, action_col2 = st.columns(2)
    
    with action_col1:
        if st.button(
            "✅ Approuver et créer compte",
            type="primary",
            use_container_width=True,
            key="approve_btn"
        ):
            with st.spinner("🔄 Traitement en cours..."):
                try:
                    # 1) Update status
                    svc.table("access_requests").update({
                        "status": "approved",
                        "reviewed_by": me,
                        "reviewed_at": now_utc_iso(),
                        "approved_role": req.get("requested_role"),
                        "last_error": None,
                        "provision_error": None,
                    }).eq("id", req["id"]).execute()
                    
                    # 2) Provision user
                    provision_user_for_access_request(
                        request_id=req["id"],
                        email=req["email"],
                        fullname=req.get("fullname"),
                        org=req.get("org"),
                        phone=req.get("phone"),
                    )
                    
                    st.success("✅ Demande approuvée avec succès !")
                    st.balloons()
                    st.rerun()
                    
                except Exception as e:
                    try:
                        svc.table("access_requests").update({
                            "last_error": str(e),
                            "provision_error": str(e),
                            "last_error_at": now_utc_iso()
                        }).eq("id", req["id"]).execute()
                    except Exception:
                        pass
                    st.error(f"❌ Échec de l'approbation : {e}")
    
    with action_col2:
        can_resend = bool(req.get("provisioned_user_id"))
        
        if st.button(
            "📩 Renvoyer identifiants",
            disabled=not can_resend,
            use_container_width=True,
            key="resend_btn"
        ):
            if not can_resend:
                st.warning("⚠️ Aucun compte n'a encore été créé pour cette demande.")
            else:
                with st.spinner("📧 Envoi en cours..."):
                    try:
                        reset_password_and_resend(
                            user_id=req["provisioned_user_id"],
                            email=req["email"],
                            fullname=req.get("fullname"),
                            request_id=req["id"],
                        )
                        
                        st.success("✅ Identifiants renvoyés avec succès !")
                        st.rerun()
                        
                    except Exception as e:
                        try:
                            svc.table("access_requests").update({
                                "last_error": f"resend failed: {e}",
                                "provision_error": f"resend failed: {e}",
                                "last_error_at": now_utc_iso()
                            }).eq("id", req["id"]).execute()
                        except Exception:
                            pass
                        st.error(f"❌ Échec de l'envoi : {e}")
    
    # Timeline
    with st.expander("📜 Historique de la demande", expanded=False):
        st.markdown(f"""
            <div class="timeline-item">
                <div class="timeline-date">Demande initiale</div>
                <div class="timeline-content">
                    {req.get('created_at', 'N/A')[:19] if req.get('created_at') else 'N/A'}
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        if req.get("provisioned_user_id"):
            st.markdown("""
                <div class="timeline-item">
                    <div class="timeline-date">Compte créé</div>
                    <div class="timeline-content">
                        ✅ Utilisateur provisionné
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        if req.get("temp_password_sent_at"):
            st.markdown(f"""
                <div class="timeline-item">
                    <div class="timeline-date">Email envoyé</div>
                    <div class="timeline-content">
                        📧 {req.get('temp_password_sent_at', 'N/A')[:19]}
                    </div>
                </div>
            """, unsafe_allow_html=True)
    
    # Données brutes
    with st.expander("🔍 Données techniques (JSON)", expanded=False):
        st.json(req)

# Footer
st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
st.caption(f"👤 Connecté en tant que : **{me}** (Super Admin)")