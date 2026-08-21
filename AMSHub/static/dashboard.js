const ctx = document.getElementById('graficoHoras');

new Chart(ctx,{
    type:'bar',

    data:{

        labels:['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'],

        datasets:[{

            label:'Horas',

            data:[4,0.5,1,3,2,0.5,1,3,0,0,0,0],

            borderRadius:8

        }]

    },

    options:{

        plugins:{
            legend:{
                display:false
            }
        },

        responsive:true,

        scales:{

            y:{
                beginAtZero:true
            }

        }

    }

});