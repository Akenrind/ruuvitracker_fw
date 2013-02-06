/*
 *  C-interfaces for Ruuvitracker Lua codes.
 *
 * @author: Seppo Takalo
 */


#include "lua.h"
#include "lualib.h"
#include "lauxlib.h"
#include "platform.h"
#include "lrotable.h"
#include "platform_conf.h"
#include "auxmods.h"
#include "sha1.h"
#include <string.h>
#include "stm32f4xx.h"


/* C-interface for Ruuvitracker codes in Lua */

static int hello( lua_State *L ) {
  lua_getglobal(L, "print");
  lua_pushstring(L, "Hello World");
  lua_pcall(L, 1, 0, 0);
  return 0;
}

/* Systick flag, it is raised on Systick interrupt handler */
extern volatile int systick;

/* Start a loop that gets runned by Systick clock intevalls */
/* Parameter: function to run on loop */
/* this function never returns */
static int idleloop( lua_State *L) {
  if (!lua_isfunction(L, -1)) {
    printf("Not a function\n");
    return 0;
  }
  for(;;) {
    lua_pushvalue(L,-1); //Get copy function to stack
    lua_pcall(L, 0, 0, 0); //Call the function

    systick=0; //Clear systick flag
    NVIC_SystemLPConfig(NVIC_LP_SLEEPONEXIT, ENABLE); //Enable SleepOnExit mode for interrupt
    while(!systick)
      __WFI(); //Go to sleep (WaitForInterrupt)
  }
  return 0;
}

#define MIN_OPT_LEVEL 2
#include "lrodefs.h"
extern const LUA_REG_TYPE sha1_map[];

const LUA_REG_TYPE ruuvi_map[] =
{
#if LUA_OPTIMIZE_MEMORY > 0
  { LSTRKEY("hello") , LFUNCVAL(hello) },
  { LSTRKEY("idleloop"), LFUNCVAL(idleloop) },
  { LSTRKEY( "sha1" ), LROVAL( sha1_map ) },
#endif
  { LNILKEY, LNILVAL }
};

LUALIB_API int luaopen_ruuvi( lua_State *L )
{
#if LUA_OPTIMIZE_MEMORY > 0
  return 0;
#else
#error "Optimize memory=0 is not supported"
#endif // #if LUA_OPTIMIZE_MEMORY > 0
}


