with tab_p:
        # --- TÍTULO ESPECÍFICO PARA ESTA SUBDIVISIÓN ---
        st.subheader("🥩 Carnes y Pescados")
        st.markdown("*Listado de productos prioritarios por fecha de vencimiento en esta área.*")
        st.divider()

        df_p = df.sort_values("Indice_Urgencia")
        for idx, r in df_p.iterrows():
            color_class = "bg-rojo" if r['Dias_Restantes'] < 0 else ("bg-naranja" if r['Indice_Urgencia'] <= 0 else "bg-verde")
            fecha_venc_str = r['Vencimiento'].strftime('%d/%m/%Y') if pd.notnull(r['Vencimiento']) else "Sin fecha"
            
            st.markdown(f"""
                <div class="card-container {color_class}">
                    <div>
                        <p class="t-blanco" style="font-size: 1.1rem;">{r['Nombre/Codigo']}</p>
                        <p class="t-blanco" style="font-size: 0.85rem; opacity: 0.9;">Vence: {fecha_venc_str} | Faltan: {r['Dias_Restantes']} días</p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            col_spacer, col_btns = st.columns([3, 1])
            with col_btns:
                c_v, c_t, c_e = st.columns(3)
                with c_v:
                    if st.button("✅", key=f"v_{idx}"):
                        df_res = df.drop(idx)
                        df_res['Produccion'] = df_res['Produccion'].dt.strftime('%d/%m/%Y')
                        df_res['Vencimiento'] = df_res['Vencimiento'].dt.strftime('%d/%m/%Y')
                        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_res)
                        st.rerun()
                with c_t:
                    if st.button("🗑️", key=f"t_{idx}"):
                        df_res = df.drop(idx)
                        df_res['Produccion'] = df_res['Produccion'].dt.strftime('%d/%m/%Y')
                        df_res['Vencimiento'] = df_res['Vencimiento'].dt.strftime('%d/%m/%Y')
                        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_res)
                        st.rerun()
                with c_e:
                    edit_mode = st.button("✏️", key=f"e_{idx}")

            if edit_mode or st.session_state.get(f"open_{idx}", False):
                st.session_state[f"open_{idx}"] = True
                with st.expander(f"✏️ Editando: {r['Nombre/Codigo']}", expanded=True):
                    en_val = st.text_input("Nombre", value=r['Nombre/Codigo'], key=f"in_n_{idx}")
                    ev_val = st.date_input("Vencimiento", value=r['Vencimiento'], key=f"in_v_{idx}", format="DD/MM/YYYY")
                    ea_val = st.slider("Aviso", 1, 30, int(r['Aviso_Dias']), key=f"in_a_{idx}")
                    
                    col_save, col_cancel = st.columns(2)
                    if col_save.button("Guardar Cambios", key=f"bs_{idx}"):
                        df.at[idx, 'Nombre/Codigo'] = en_val
                        df.at[idx, 'Vencimiento'] = pd.to_datetime(ev_val)
                        df.at[idx, 'Aviso_Dias'] = ea_val
                        df_s = df.copy()
                        df_s['Produccion'] = df_s['Produccion'].dt.strftime('%d/%m/%Y')
                        df_s['Vencimiento'] = df_s['Vencimiento'].dt.strftime('%d/%m/%Y')
                        conn.update(spreadsheet=url, worksheet="Hoja 1", data=df_s)
                        st.session_state[f"open_{idx}"] = False
                        st.rerun()
                    if col_cancel.button("Cerrar", key=f"bc_{idx}"):
                        st.session_state[f"open_{idx}"] = False
                        st.rerun()
