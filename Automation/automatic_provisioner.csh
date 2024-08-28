#!/usr/bin/csh 

#
#############################################
##
##  This file should be used to populate
##  automatically all data in the HSS node
##  for testing purposes
##
#############################################

set narg = $#argv

switch ($narg)

  case 1:

    echo "Number of arguments = "$narg
    echo "Macro file to process = "$1

    set macro_file = $1

    ls -la $macro_file

    if ($?) then
      echo
      echo "*** ERROR: I cannot find the macro file stated as argumment"
      echo
      exit 1
    else
      echo
      echo "Macro file identified"
      echo
      
      set lines = `cat $1| egrep -v "\/\/|#"`
      
    endif

  breaksw

  default:

      echo ""
      echo " *** ERROR ON ARGUMENTS: Macro file missing."
      echo ""

      exit 1

  breaksw

endsw

#################################################################


set step = 1
set i = 1


set LDAPERRORS_DIR = $LDAPERRORS
mkdir -p $LDAPERRORS_DIR
rm -fr $LDAPERRORS_DIR/*.error

set LDAPERRORS = $LDAPERRORS_DIR/automatic_provisioner.error
touch $LDAPERRORS


while ( $i <= $#lines )

  set step_action = `echo $lines[$i] | egrep '^[ \t]*STEP'  | cut -d"|" -f2 | cut -d":" -f1`

  echo
  echo "Action to perform: $step_action"
  echo "Step: $i" >> $LDAPERRORS
  echo "Action to perform: $lines[$i]" >> $LDAPERRORS
  echo

  switch ($step_action)

    case POPULATE_ISM_SDA_NODE:

      echo ""    
      echo "POPULATE ISM SDA NODE:"
      echo ""

      set data_file = `echo $lines[$i] | egrep '^[ \t]*STEP'  | cut -d":" -f3`
  
      if (`ls "$CCRC_VIEW_PATH$data_file" | grep -c ""` == "1") then
       
        $CCRC_VIEW_PATH/vobs/hss/hss_code/system_test/BAT/ISM_SDA/populate/data_transcript/populate_hss_node_data.csh "$CCRC_VIEW_PATH$data_file"

      else

 	echo
 	echo " *** ERROR: $data_file not found" 
 	echo " *** ERROR: $data_file not found" >> $LDAPERRORS
 	echo

      endif
      


    breaksw

    ######

    case POPULATE_ESM_NODE:

      echo ""
      echo "POPULATE ESM NODE:"
      echo ""

      set data_file = `echo $lines[$i] | egrep '^[ \t]*STEP'  | cut -d":" -f3`

      $CCRC_VIEW_PATH/vobs/hss/hss_code/system_test/BAT/ESM/populate/data_transcript/populate_esm_node_data.csh "$CCRC_VIEW_PATH$data_file"

    breaksw

    ######

    case POPULATE_AVG_NODE:

      echo ""
      echo "POPULATE AVG NODE:"
      echo ""

      $CCRC_VIEW_PATH/vobs/hss/hss_code/system_test/BAT/AVG/populate/data_transcript/populate_avg_node_data.csh

    breaksw

    ######

    case POPULATE_SM_NODE:

      echo ""
      echo "POPULATE SM NODE:"
      echo ""

      $CCRC_VIEW_PATH/vobs/hss/hss_code/system_test/BAT/SM/populate/data_transcript/populate_sm_node_data.csh

    breaksw

    ######

    case POPULATE_ISM_SDA_SUBS_MO:
   
      echo "" 
      echo "POPULATE ISM SDA SUBS on HSS MO Node"
      echo "" 

      set data_file = `echo $lines[$i] | egrep '^[ \t]*STEP'  | cut -d":" -f3`

      if (`ls "$CCRC_VIEW_PATH$data_file" | grep -c ""` == "1") then

         $CCRC_VIEW_PATH/vobs/hss/hss_code/system_test/BAT/ISM_SDA/populate/data_transcript/populate_hss_subs_data.csh "$CCRC_VIEW_PATH$data_file" ${step}

      else

 	echo
 	echo " *** ERROR: $data_file not found" 
 	echo " *** ERROR: $data_file not found" >> $LDAPERRORS
 	echo

      endif


    breaksw


    case DELETE_ISM_SDA_SUBS_MO:
   
      echo "" 
      echo "DELETE ISM SDA SUBS on HSS MO Node"
      echo "" 

      set data_file = `echo $lines[$i] | egrep '^[ \t]*STEP'  | cut -d":" -f3`

      if (`ls "$CCRC_VIEW_PATH$data_file" | grep -c ""` == "1") then

         $CCRC_VIEW_PATH/vobs/hss/hss_code/system_test/BAT/ISM_SDA/populate/data_transcript/delete_hss_subs_data.csh "$CCRC_VIEW_PATH$data_file" ${step}

      else

 	echo
 	echo " *** ERROR: $data_file not found" 
 	echo " *** ERROR: $data_file not found" >> $LDAPERRORS
 	echo

      endif


    breaksw

    ######

    case POPULATE_ESM_SUBS_MO:

      echo ""
      echo "POPULATE ESM SUBS on HSS MO Node"
      echo ""

      set data_file = `echo $lines[$i] | egrep '^[ \t]*STEP'  | cut -d":" -f3`

      if (`ls "$CCRC_VIEW_PATH$data_file" | grep -c ""` == "1") then

          $CCRC_VIEW_PATH/vobs/hss/hss_code/system_test/BAT/ESM/populate/data_transcript/populate_esm_subs_on_MO.csh "$CCRC_VIEW_PATH$data_file" ${step}

      else

 	echo
 	echo " *** ERROR: $data_file not found" 
 	echo " *** ERROR: $data_file not found" >> $LDAPERRORS
 	echo

      endif


    breaksw

    ######

    case POPULATE_ESM_MME:

      echo ""
      echo "POPULATE ESM MME on HSS"
      echo ""

      set data_file = `echo $lines[$i] | egrep '^[ \t]*STEP'  | cut -d":" -f3`

      if (`ls "$CCRC_VIEW_PATH$data_file" | grep -c ""` == "1") then

          $CCRC_VIEW_PATH/vobs/hss/hss_code/system_test/BAT/ESM/populate/data_transcript/populate_esm_mme.csh "$CCRC_VIEW_PATH$data_file" ${step}

      else

 	echo
 	echo " *** ERROR: $data_file not found" 
 	echo " *** ERROR: $data_file not found" >> $LDAPERRORS
 	echo

      endif


    breaksw

    ######

   case DELETE_ESM_SUBS_MO:

      echo ""
      echo "DELETE ESM SUBS on HSS MO Node"
      echo ""

      set data_file = `echo $lines[$i] | egrep '^[ \t]*STEP'  | cut -d":" -f3`

      if (`ls "$CCRC_VIEW_PATH$data_file" | grep -c ""` == "1") then

          $CCRC_VIEW_PATH/vobs/hss/hss_code/system_test/BAT/ESM/populate/data_transcript/delete_esm_subs_on_MO.csh "$CCRC_VIEW_PATH$data_file" ${step}

      else

 	echo
 	echo " *** ERROR: $data_file not found" 
 	echo " *** ERROR: $data_file not found" >> $LDAPERRORS
 	echo

      endif


    breaksw

    ######

    case POPULATE_AVG_SUBS_MO:

      echo ""
      echo "POPULATE AVG SUBS on HSS MO Node"
      echo ""

      set data_file = `echo $lines[$i] | egrep '^[ \t]*STEP'  | cut -d":" -f3`

      if (`ls "$CCRC_VIEW_PATH$data_file" | grep -c ""` == "1") then

          $CCRC_VIEW_PATH/vobs/hss/hss_code/system_test/BAT/AVG/populate/data_transcript/populate_avg_subs_on_MO.csh "$CCRC_VIEW_PATH$data_file" ${step}

      else

 	echo
 	echo " *** ERROR: $data_file not found" 
 	echo " *** ERROR: $data_file not found" >> $LDAPERRORS
 	echo

      endif


    breaksw

    ######

    case POPULATE_AAA_NODE:

      echo "" 
      echo "POPULATE AAA NODE DATA"
      echo "" 

      set data_file = `echo $lines[$i] | egrep '^[ \t]*STEP'  | cut -d":" -f3`

      if (`ls "$CCRC_VIEW_PATH$data_file" | grep -c ""` == "1") then

      	set proxy_AAA = `grep PROXY "$CCRC_VIEW_PATH$data_file" | cut -f2`
      	set ppas_AAA = `grep PPAS "$CCRC_VIEW_PATH$data_file" | cut -f2`

      	setenv PROXY $proxy_AAA
      	setenv PPAS $ppas_AAA

	$CCRC_VIEW_PATH/vobs/hss/hss_code/system_test/BAT/AAA/populate/data_transcript/populate_aaa_data.csh "$CCRC_VIEW_PATH$data_file"

      else

 	echo
 	echo " *** ERROR: $data_file not found" 
 	echo " *** ERROR: $data_file not found" >> $LDAPERRORS
 	echo

      endif


    breaksw

    ######
    
    case POPULATE_WSM_NODE:

      echo ""    
      echo "POPULATE WSM NODE DATA:"
      echo ""

      set data_file = `echo $lines[$i] | egrep '^[ \t]*STEP'  | cut -d":" -f3`
      
      if (`ls "$CCRC_VIEW_PATH$data_file" | grep -c ""` == "1") then

          $CCRC_VIEW_PATH/vobs/hss/hss_code/system_test/BAT/WLAN/populate/populate_wsm_data.csh "$CCRC_VIEW_PATH$data_file"

      else

 	echo
 	echo " *** ERROR: $data_file not found" 
 	echo " *** ERROR: $data_file not found" >> $LDAPERRORS
 	echo

      endif      


    breaksw

    ######

    case POPULATE_RADIUS_CLIENTS:

      echo ""
      echo "POPULATE RADIUS CLIENTS"
      echo ""

      set data_file = `echo $lines[$i] | egrep '^[ \t]*STEP'  | cut -d":" -f3`
	      
      if (`ls "$data_file" | grep -c ""` == "1") then

         $CCRC_VIEW_PATH/vobs/hss/hss_code/system_test/BAT/RADIUS/populate/data_transcript/populate_RADIUS_clients.csh "$data_file"
      else

 	echo
 	echo " *** ERROR: $data_file not found" 
 	echo " *** ERROR: $data_file not found" >> $LDAPERRORS
 	echo

      endif


    breaksw

    ######

    case CREATE_BACKUP:

      echo ""
      echo "CREATE BACKUP"
      echo ""

      echo
      echo "Starting backup request..."
      echo

      set backup_name = `echo $lines[$i] | egrep '^[ \t]*STEP'  | cut -d":" -f3`

      TSP_create_backup --node $IO2_IP $backup_name

      set backup_result = $?

      if ( "$backup_result" == "0" ) then

        echo "Backup $backup_name created successfully on $IO2_IP"

      else

	echo "###### ERROR ######"
        echo " *** ERROR: Backup $backup_name on $IO2_IP is getting an error" 
        echo " *** ERROR: Backup $backup_name on $IO2_IP is getting an error" >> $LDAPERRORS
	echo "###### ERROR ######"

      endif


      if ( "$IO2_IP" != "$SLF_IO2_IP" ) then

      	TSP_create_backup --node $SLF_IO2_IP $backup_name

      	set backup_result = $?

      	if ( "$backup_result" == "0" ) then

        	echo "Backup $backup_name created successfully on $SLF_IO2_IP"

      	else

		echo "###### ERROR ######"
        	echo " *** ERROR: Backup $backup_name on $SLF_IO2_IP is getting an error" 
        	echo " *** ERROR: Backup $backup_name on $SLF_IO2_IP is getting an error" >> $LDAPERRORS
		echo "###### ERROR ######"

      	endif

      endif



    breaksw

    ######

    case CREATE_SECONDARY_BACKUP:

      echo ""
      echo "CREATE BACKUP"
      echo ""

      echo
      echo "Starting backup request..."
      echo

      set backup_name = `echo $lines[$i] | egrep '^[ \t]*STEP'  | cut -d":" -f3`

      TSP_create_backup --node $SECONDARY_IO2_IP $backup_name

      set backup_result = $?

      if ( "$backup_result" == "0" ) then

        echo "Backup $backup_name created successfully on $SECONDARY_IO2_IP"

      else

	echo "###### ERROR ######"
        echo " *** ERROR: Backup $backup_name on $SECONDARY_IO2_IP is getting an error" 
        echo " *** ERROR: Backup $backup_name on $SECONDARY_IO2_IP is getting an error" >> $LDAPERRORS
	echo "###### ERROR ######"

      endif


    breaksw

    ######
    case CREATE_SLF_BACKUP:

      echo ""
      echo "CREATE SLF BACKUP"
      echo ""

      echo
      echo "Starting backup request..."
      echo

      set backup_name = `echo $lines[$i] | egrep '^[ \t]*STEP'  | cut -d":" -f3`

      TSP_create_backup --node $SLF_IO2_IP $backup_name

      set backup_result = $?

      if ( "$backup_result" == "0" ) then

        echo "Backup $backup_name created successfully"

      else

	echo "###### ERROR ######"
        echo " *** ERROR: Backup $backup_name is getting an error" 
        echo " *** ERROR: Backup $backup_name is getting an error" >> $LDAPERRORS
	echo "###### ERROR ######"

      endif

    breaksw

    ######
    case CREATE_EXTERNAL_BACKUP:

      echo ""
      echo "CREATE EXTERNAL BACKUP"
      echo ""

      echo
      echo "Starting backup request..."
      echo

      set backup_name = `echo $lines[$i] | egrep '^[ \t]*STEP'  | cut -d":" -f3`

      GTLA_create_backup --node $EXT_DB_OAM_IP $backup_name

      set backup_result = $?

      if ( "$backup_result" == "0" ) then

        echo "Backup $backup_name created successfully"

      else

	echo "###### ERROR ######"
        echo " *** ERROR: Backup $backup_name is getting an error" 
        echo " *** ERROR: Backup $backup_name is getting an error" >> $LDAPERRORS
	echo "###### ERROR ######"

      endif

    breaksw

    case ACTIVATE_EXTERNAL_BACKUP:

      echo ""
      echo "ACTIVATE EXTERNAL BACKUP"
      echo ""

      echo
      echo "Starting activate request..."
      echo

      set backup_name = `echo $lines[$i] | egrep '^[ \t]*STEP'  | cut -d":" -f3`

      GTLA_restore_backup --node $EXT_DB_OAM_IP -b $backup_name

      set backup_result = $?

      if ( "$backup_result" == "0" ) then

        echo "Backup $backup_name activateted successfully"

      else

	echo "###### ERROR ######"
        echo " *** ERROR: Backup $backup_name is getting an error" 
        echo " *** ERROR: Backup $backup_name is getting an error" >> $LDAPERRORS
	echo "###### ERROR ######"

      endif

    breaksw

    ######

    case POPULATE_HSI_NODE:

      	echo ""    
      	echo "POPULATE HSI NODE:"
      	echo ""

         $CCRC_VIEW_PATH/vobs/hss/hss_code/system_test/BAT/HSI/populate/data_transcript/populate_hsi_node_data.csh

    breaksw


    ######
    
    case POPULATE_SLF_NODE_REDIRECT:

      	echo ""    
      	echo "POPULATE SLF NODE REDIRECT:"
      	echo ""

         $CCRC_VIEW_PATH/vobs/hss/hss_code/system_test/BAT/SLF/populate/data_transcript/populate_slf_MO_redirect_node_data.csh

    breaksw


    ######
    
    case POPULATE_SLF_NODE_PROXY:

      	echo ""    
      	echo "POPULATE SLF NODE:"
      	echo ""

         $CCRC_VIEW_PATH/vobs/hss/hss_code/system_test/BAT/SLF/populate/data_transcript/populate_slf_proxy_node_data.csh

    breaksw


    ######
    
        case POPULATE_SLF_NODE_DBPROXY:

      	echo ""    
      	echo "POPULATE SLF NODE DBPROXY FOR ISM:"
      	echo ""

         $CCRC_VIEW_PATH/vobs/hss/hss_code/system_test/BAT/SLF/populate/data_transcript/populate_slf_MO_DBProxy_node_data.csh

    breaksw

    ######
    
        case POPULATE_SLF_NODE_PROXY_MO_ESM:

      	echo ""    
      	echo "POPULATE SLF NODE DBPROXY FOR ESM:"
      	echo ""

         $CCRC_VIEW_PATH/vobs/hss/hss_code/system_test/BAT/SLF/populate/data_transcript/populate_slf_MO_DBProxy_node_esm_data.csh

    breaksw

    ######

        case POPULATE_SLF_NODE_PROXY_LA_ESM:

      	echo ""    
      	echo "POPULATE SLF NODE PROXY LA FOR ESM-AVG:"
      	echo ""

         $CCRC_VIEW_PATH/vobs/hss/hss_code/system_test/BAT/SLF/populate/data_transcript/populate_slf_LA_DBProxy_node_esm_data.csh

    breaksw


    ######
    
        case POPULATE_SLF_NODE_PROXY_LA_ISM:

      	echo ""    
      	echo "POPULATE SLF NODE PROXY LA FOR ISM-SDA:"
      	echo ""


         $CCRC_VIEW_PATH/vobs/hss/hss_code/system_test/BAT/SLF/populate/data_transcript/populate_slf_LA_DBProxy_node_ism_data.csh

    breaksw


    ######

    case POPULATE_SLF_SUBS:

      echo "" 
      echo "POPULATE SLF SUBS"
      echo "" 

      set data_file = `echo $lines[$i] | egrep '^[ \t]*STEP'  | cut -d":" -f3`

      if (`ls "$CCRC_VIEW_PATH$data_file" | grep -c ""` == "1") then

         $CCRC_VIEW_PATH/vobs/hss/hss_code/system_test/BAT/SLF/populate/data_transcript/populate_slf_subs_data.csh "$CCRC_VIEW_PATH$data_file" ${step}

      else

 	echo
 	echo " *** ERROR: $data_file not found" 
 	echo " *** ERROR: $data_file not found" >> $LDAPERRORS
 	echo

      endif

    breaksw

    ######
    
    case POPULATE_EXT_DB_FE:

      echo "" 
      echo "POPULATE ExtDb Front End"
      echo "" 

      set data_file = `echo $lines[$i] | egrep '^[ \t]*STEP'  | cut -d":" -f3`

      if (`ls "$CCRC_VIEW_PATH$data_file" | grep -c ""` == "1") then

         $CCRC_VIEW_PATH/vobs/hss/hss_code/system_test/BAT/DAL/populate/data_transcript/populate_on_fe_extdb_data.csh "$CCRC_VIEW_PATH$data_file"

      else

 	echo
 	echo " *** ERROR: $data_file not found" 
 	echo " *** ERROR: $data_file not found" >> $LDAPERRORS
 	echo

      endif

    breaksw

    ######
    
    case POPULATE_SCHEMA:

      echo "" 
      echo "POPULATE SCHEMA"
      echo "" 

      set data_file = `echo $lines[$i] | egrep '^[ \t]*STEP'  | cut -d":" -f3`

      if (`ls "$CCRC_VIEW_PATH$data_file" | grep -c ""` == "1") then

         $CCRC_VIEW_PATH/vobs/hss/hss_code/system_test/BAT/DAL/populate/data_transcript/populate_hss-be_node_data.csh "$CCRC_VIEW_PATH$data_file"

      else

 	echo
 	echo " *** ERROR: $data_file not found" 
 	echo " *** ERROR: $data_file not found" >> $LDAPERRORS
 	echo

      endif

    breaksw

    ######
     case POPULATE_HLR_SCHEMA:

      echo "" 
      echo "POPULATE SCHEMA"
      echo "" 

      set data_file = `echo $lines[$i] | egrep '^[ \t]*STEP'  | cut -d":" -f3`

      if (`ls "$CCRC_VIEW_PATH$data_file" | grep -c ""` == "1") then

         $CCRC_VIEW_PATH/vobs/hss/hss_code/system_test/BAT/DAL/populate/data_transcript/populate_hlr-be_node_data.csh "$CCRC_VIEW_PATH$data_file"

      else

 	echo
 	echo " *** ERROR: $data_file not found" 
 	echo " *** ERROR: $data_file not found" >> $LDAPERRORS
 	echo

      endif

    breaksw

    ######
   
    case POPULATE_LA_SUBS:

      echo "" 
      echo "POPULATE SUBS ON EXTDB"
      echo "" 

      set data_file = `echo $lines[$i] | egrep '^[ \t]*STEP'  | cut -d":" -f3`
      set edb_file = `echo $lines[$i] | egrep '^[ \t]*STEP'  | cut -d":" -f4`

      if (`ls "$CCRC_VIEW_PATH$data_file" | grep -c ""` == "1") then

      	if (`ls "$CCRC_VIEW_PATH$edb_file" | grep -c ""` == "1") then

         	$CCRC_VIEW_PATH/vobs/hss/hss_code/system_test/BAT/DAL/populate/data_transcript/populate_subs_on_LA.csh "$CCRC_VIEW_PATH$data_file" "$CCRC_VIEW_PATH$edb_file" ${step}

      	else

 		echo
 		echo " *** ERROR: $edb_file not found" 
 		echo " *** ERROR: $edb_file not found" >> $LDAPERRORS
 		echo

      	endif

      else

 	echo
 	echo " *** ERROR: $data_file not found" 
 	echo " *** ERROR: $data_file not found" >> $LDAPERRORS
 	echo

      endif

    breaksw

    ######
     case DELETE_LA_SUBS:

      echo "" 
      echo "DELETE SUBS ON EXTDB"
      echo "" 

      set data_file = `echo $lines[$i] | egrep '^[ \t]*STEP'  | cut -d":" -f3`
      set edb_file = `echo $lines[$i] | egrep '^[ \t]*STEP'  | cut -d":" -f4`

      if (`ls "$CCRC_VIEW_PATH$data_file" | grep -c ""` == "1") then

      	if (`ls "$CCRC_VIEW_PATH$edb_file" | grep -c ""` == "1") then

         	$CCRC_VIEW_PATH/vobs/hss/hss_code/system_test/BAT/DAL/populate/data_transcript/delete_subs_on_LA.csh "$CCRC_VIEW_PATH$data_file" "$CCRC_VIEW_PATH$edb_file" ${step}

      	else

 		echo
 		echo " *** ERROR: $edb_file not found" 
 		echo " *** ERROR: $edb_file not found" >> $LDAPERRORS
 		echo

      	endif

      else

 	echo
 	echo " *** ERROR: $data_file not found" 
 	echo " *** ERROR: $data_file not found" >> $LDAPERRORS
 	echo

      endif

    breaksw

    ######   default:

        echo
        echo " *** This line on macro doesn't make any action" >> $LDAPERRORS
        echo " ***      $lines[$i]" >> $LDAPERRORS
        echo

    breaksw

  endsw

  @ i = $i + 1
  set step =  `expr $step + 1`

end

echo
echo
echo " ================================= "
echo " ================================= "
echo "       POPULATION IS FINISHED "
echo "   THIS WINDOW CAN BE CLOSED NOW"
echo " ================================= "
echo " ================================= "
echo
echo

